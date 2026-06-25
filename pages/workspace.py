# pages/workspace.py
import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
from datetime import datetime
import re

# Import banking core modules
from services.pdf_reader import extract_text
from services.statement_validator import build_validation_report
from services.xml_generator import generate_tally_xml
from services.xlsx_viewer import export_xml_audit_workbook

# Import Ashramam Custom Modules
from parsers.cash_parser import parse_cash_workbook, MAPPING_FILE, load_lexicon, save_lexicon
from services.cash_validator import run_cash_audit
from services.cash_xlsx_writer import build_nested_tally_sheets
from services.cash_xml_generator import generate_ashramam_tally_xml

st.set_page_config(page_title="Workspace | Tally Automation", layout="wide")

if st.button("⬅️ Back to Information Page", type="secondary"):
    st.switch_page("app.py")

st.title("📊 Financial Statement to Tally XML Engine")
st.markdown("Upload your bank statement file or multi-tab cash receipts workbook below.")

os.makedirs("temp_uploads", exist_ok=True)

# -------------------------------------------------------------
# SIDEBAR CONTROLS
# -------------------------------------------------------------
st.sidebar.header("⚙️ Configuration Settings")

bank_type = st.sidebar.selectbox(
    "1. Select Statement Processing Type",
    ["Bank of Baroda (BOB)", "State Bank of India (SBI)", "Ashramam Cash Receipts Ledger"]
)

if bank_type == "Ashramam Cash Receipts Ledger":
    file_types = ["xlsx", "csv"]
    help_msg = "Select a strict A,B,C,D,E format ledger workbook spreadsheet"
else:
    file_types = ["pdf"]
    help_msg = "Select a digital bank e-statement document"

uploaded_file = st.sidebar.file_uploader(
    f"2. Upload Source File ({', '.join(file_types).upper()})", 
    type=file_types,
    help=help_msg,
    key="file_uploader_widget"
)

# FIXED: Expose the timeline filtration parameter for BOTH banking layouts and the Ashramam ledger
st.sidebar.markdown("📅 **Timeline Slicing Parameter**")
boundary_date_input = st.sidebar.date_input(
    "Process transactions ON or AFTER this date:",
    value=datetime(2025, 4, 1)
)

strategy_type = "Whole Document"
if bank_type != "Ashramam Cash Receipts Ledger":
    strategy_type = st.sidebar.selectbox(
        "3. Select Ingestion Strategy", 
        ["Full bank statement", "Incomplete statement (Continuation)"]
    )
    
    prev_balance = None
    if strategy_type == "Incomplete statement (Continuation)":
        prev_balance_str = st.sidebar.text_input(
            "Enter Previous/Starting Balance (defaults to 0.00):",
            value="",
            help="Providing the ending balance of the previous statement ensures correct inference of the first transaction type."
        )
        if prev_balance_str.strip():
            try:
                prev_balance = float(prev_balance_str.strip().replace(",", ""))
            except ValueError:
                st.sidebar.error("Invalid balance format. Please enter a valid number.")

convert_btn = st.sidebar.button("Convert File Now", use_container_width=True, disabled=not uploaded_file)

# -------------------------------------------------------------
# STEP-BY-STEP CONVERSION PIPELINE
# -------------------------------------------------------------
if uploaded_file and convert_btn:
    for key in ["xml", "report", "xlsx","pdf", "is_ashramam", "conversion_complete", "flagged_names_map", "files_ready", "saved_bank_ledger", "saved_suspense_ledger", "saved_cutoff_date"]:
        if key in st.session_state:
           del st.session_state[key]

    temp_file_path = os.path.join("temp_uploads", uploaded_file.name)
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
        
    if bank_type == "Ashramam Cash Receipts Ledger":
        with st.status("🔮 Running Ashramam Ledger Pipeline...", expanded=True) as status_box:
            try:
                st.write("⏳ Step 1: Running strict A,B,C,D,E verification guardrails & filtering out the...")
                uploaded_file.seek(0)
                
                # Save chosen filter date to session state memory right away
                st.session_state["saved_cutoff_date"] = boundary_date_input
                
                # Pass filtration parameter directly into engine
                transactions, flagged_map,master_names_map = parse_cash_workbook(uploaded_file, start_date_cutoff=st.session_state["saved_cutoff_date"]) 
                
                st.write("⏳ Step 2: Running cash entry audit pipelines...")
                audit_report = run_cash_audit(transactions)
                
                st.write("⏳ Step 3: Generating multi-sheet Tally preview ledger...")
                excel_preview = build_nested_tally_sheets(transactions)
                
                st.session_state["raw_transactions"] = transactions
                st.session_state["report"] = audit_report
                st.session_state["xlsx"] = excel_preview
                st.session_state["flagged_names_map"] = flagged_map
                st.session_state["master_names_map"] = master_names_map
                st.session_state["conversion_complete"] = True
                st.session_state["is_ashramam"] = True
                
                status_box.update(label="✅ Ashramam Processing Chain Complete!", state="complete")
            except ValueError as val_err:
                status_box.update(label="❌ Strict Structural Validation Failed", state="error")
                st.error(str(val_err))
                st.stop()
            except Exception as e:
                st.error(f"❌ Conversion System Failure: {str(e)}")
                status_box.update(label="❌ Conversion Error", state="error")
            finally:
                if os.path.exists(temp_file_path): os.remove(temp_file_path)
                
    else:
        with st.status("🛠️ Running Conversion Engine...", expanded=True) as status_box:
            try:
                st.write("⏳ Step 1: Extracting text matrix layers from PDF source...")
                text = extract_text(temp_file_path)
                from parsers.router import verify_bank_profile, route_to_parser
                if not verify_bank_profile(bank_type, text):
                    status_box.update(label="❌ Bank Selection Mismatch", state="error")
                else:
                    st.write(f"⏳ Step 2: Applying Ingestion Strategy: [{strategy_type}]...")
                    from parsers.bob_parser import parse_opening_balance as parse_bob_opening
                    from parsers.sbi_parser import parse_opening_balance as parse_sbi_opening
                    from strategies import WholeChunk, FirstChunk, ContinuationChunk
                    
                    parse_opening_func = parse_bob_opening if "BOB" in bank_type else parse_sbi_opening
                    if strategy_type == "Full bank statement":
                        sanitized_text, opening_bal = WholeChunk.process_strategy(text, parse_opening_func)
                    elif strategy_type == "Incomplete statement (Continuation)":
                        sanitized_text, _ = ContinuationChunk.process_strategy(text, parse_opening_func, bank_type, boundary_date_input)
                        opening_bal = prev_balance
                    else:
                        sanitized_text, opening_bal = WholeChunk.process_strategy(text, parse_opening_func)

                    st.write("⏳ Step 3: Extracting transaction records row-by-row...")
                    transactions = route_to_parser(bank_type, sanitized_text, opening_balance=opening_bal)
                    
                    st.session_state["raw_transactions"] = transactions
                    st.session_state["sanitized_text"] = sanitized_text
                    st.session_state["opening_balance"] = opening_bal
                    st.session_state["conversion_complete"] = True
                    st.session_state["is_ashramam"] = False
                    status_box.update(label="✅ Step-By-Step Data Extraction Complete!", state="complete")
            except Exception as e:
                st.error(f"❌ Conversion Failed: {str(e)}")
            finally:
                if os.path.exists(temp_file_path): os.remove(temp_file_path)

# -------------------------------------------------------------
# UNIFIED ATOMIC OPERATION FORM 
# -------------------------------------------------------------
# -------------------------------------------------------------
# UNIFIED ATOMIC OPERATION FORM 
# -------------------------------------------------------------
if "conversion_complete" in st.session_state:
    is_ashramam = st.session_state.get("is_ashramam", False)
    flagged_names = st.session_state.get("flagged_names_map", {})
    master_names_map = st.session_state.get("master_names_map", {}) 
    has_audit_flags = is_ashramam and len(flagged_names) > 0
    
    st.divider()
    
    if "saved_bank_ledger" not in st.session_state:
        st.session_state["saved_bank_ledger"] = "Cash" if is_ashramam else ("BANK OF BARODA" if "BOB" in bank_type else "STATE BANK OF INDIA")
    if "saved_suspense_ledger" not in st.session_state:
        st.session_state["saved_suspense_ledger"] = "Annadana Prasadam Donations Received" if is_ashramam else "Suspense"
    if "saved_cutoff_date" not in st.session_state:
        st.session_state["saved_cutoff_date"] = None
        
    trigger_reprocess = False  

    with st.form("unified_tally_submission_form"):
        st.subheader("🎯 Final Step: Align with your Tally Ledger Name")
        col_led1, col_led2 = st.columns(2) 
        
        with col_led1: 
            final_bank_ledger = st.text_input("Debit Ledger Name (Tally Cash/Bank Account):", value=st.session_state["saved_bank_ledger"])
        with col_led2:
            final_suspense_ledger = st.text_input("Credit Ledger Name (Tally Particulars Account):", value=st.session_state["saved_suspense_ledger"])
            
        # -------------------------------------------------------------
        # CONDITIONAL DOCK: Only show Lexicon Desk for Ashramam Ledger
        # -------------------------------------------------------------
        if is_ashramam:
            st.markdown("---")
            st.subheader("📋 Translation & Lexicon Management Desk")
            
            # Define structural layout tabs
            tab_critical, tab_master = st.tabs([
                f"⚠️ Critical System Flags ({len(flagged_names)})", 
                f"🗂️ Complete Directory Review ({len(master_names_map)})"
            ])
            
            # --- TAB 1: CRITICAL FLAGS ---
            with tab_critical:
                audit_rows = []
                for k, v in flagged_names.items():
                    clean_k = k.strip().replace("గారూ", "").replace("గారు", "").replace("-", " ").replace("—", " ")
                    clean_k = re.sub(r'\s+', ' ', clean_k).strip()
                    
                    audit_rows.append({
                        "Original Telugu Input": clean_k, 
                        "Suggested English Translation": v
                    })
                    
                df_audit = pd.DataFrame(audit_rows)

                if has_audit_flags:
                    st.markdown("---")
                    st.subheader(f"🔍 Name Verification Guardrail (Flagged Records: {len(flagged_names)})")
                    st.warning("Review misspelled text names or accent anomalies directly inside the interactive grid row layout below.")
                    
                    edited_df = st.data_editor(
                        df_audit,
                        use_container_width=True,
                        disabled=["Original Telugu Input"],
                        column_config={
                            "Suggested English Translation": st.column_config.TextColumn(
                                "Corrected English Name",
                                help="Type the clean plain English name here. It will instantly overwrite the system database.",
                                required=True,
                        )
                        },
                        key="critical_audit_editor" # Fixed key mismatch vs state parsing
                    )
                else:
                    st.success("🟢 No severe naming format anomalies detected in this timeline block!")
            
            # --- TAB 2: COMPLETE DIRECTORY REVIEW ---
            with tab_master:
                st.info("This directory displays every unique name parsed from your cutoff slice. Modify any mapping to change how it outputs to Tally and Excel.")
                
                master_rows = []
                for k, v in master_names_map.items():
                    clean_k = k.strip().replace("గారూ", "").replace("గారు", "").replace("-", " ").replace("—", " ")
                    clean_k = re.sub(r'\s+', ' ', clean_k).strip()
                    master_rows.append({"Original Telugu Input": clean_k, "Target English Translation": v})
                
                df_master = pd.DataFrame(master_rows)
                
                st.metric("Total Unique Donors in Current View", f"{len(df_master):,}")
                
                edited_master_df = st.data_editor(
                    df_master,
                    use_container_width=True,
                    disabled=["Original Telugu Input"],
                    key="master_directory_editor"
                )
        
        st.write(" ")
        submit_all_btn = st.form_submit_button("Lock Settings & Generate Download Files 🔒", type="primary", use_container_width=True)

    
    if submit_all_btn:
        st.session_state["saved_bank_ledger"] = final_bank_ledger
        st.session_state["saved_suspense_ledger"] = final_suspense_ledger

        critical_state = st.session_state.get("critical_audit_editor", {}).get("edited_rows", {}) if st.session_state.get("critical_audit_editor") else {}
        master_state = st.session_state.get("master_directory_editor", {}).get("edited_rows", {}) if st.session_state.get("master_directory_editor") else {}
        
        
        
        # if critical_state or master_state:
        #     master_lexicon = load_lexicon()
        #     updated_counter = 0
            
        #     # # Apply changes from Critical Data Editor Tab
        #     # for row_idx_str, changes in critical_state.items():
        #     #     if "Suggested English Translation" in changes:
        #     #         row_idx = int(row_idx_str)
        #     #         telugu_key = df_audit.iloc[row_idx]["Original Telugu Input"]
        #     #         user_english = changes["Suggested English Translation"].strip()
        #     #         if user_english:
        #     #             master_lexicon[telugu_key] = user_english
        #     #             updated_counter += 1

        #     # # Apply changes from Master Directory Data Editor Tab
        #     # for row_idx_str, changes in master_state.items():
        #     #     if "Target English Translation" in changes:
        #     #         row_idx = int(row_idx_str)
        #     #         telugu_key = df_master.iloc[row_idx]["Original Telugu Input"]
        #     #         user_english = changes["Target English Translation"].strip()
        #     #         if user_english:
        #     #             master_lexicon[telugu_key] = user_english
        #     #             updated_counter += 1
            
        #     # Helper function to break down phrases and map individual word positions
        #     def save_split_tokens(telugu_phrase, english_phrase, lexicon_dict):
        #         t_words = telugu_phrase.strip().split()
        #         e_words = english_phrase.strip().split()
                
        #         # Case 1: Ideal 1-to-1 word count match (e.g., 5 Telugu words edited to 5 English words)
        #         if len(t_words) == len(e_words):
        #             saved_any = False
        #             for tw, ew in zip(t_words, e_words):
        #                 if lexicon_dict.get(tw) != ew:
        #                     lexicon_dict[tw] = ew
        #                     saved_any = True
        #             return saved_any
        #         else:
        #             # Case 2: Unequal counts (e.g., 5 Telugu words compressed to 2 English words)
        #             # Fallback to saving the entire string mapping so things don't break
        #             if lexicon_dict.get(telugu_phrase) != english_phrase:
        #                 lexicon_dict[telugu_phrase] = english_phrase
        #                 return True
        #         return False

        #     # Apply word-split changes from Critical Data Editor Tab
        #     for row_idx_str, changes in critical_state.items():
        #         if "Suggested English Translation" in changes:
        #             row_idx = int(row_idx_str)
        #             telugu_key = df_audit.iloc[row_idx]["Original Telugu Input"]
        #             user_english = changes["Suggested English Translation"].strip()
        #             if user_english:
        #                 if save_split_tokens(telugu_key, user_english, master_lexicon):
        #                     updated_counter += 1

        #     # Apply word-split changes from Master Directory Data Editor Tab
        #     for row_idx_str, changes in master_state.items():
        #         if "Target English Translation" in changes:
        #             row_idx = int(row_idx_str)
        #             telugu_key = df_master.iloc[row_idx]["Original Telugu Input"]
        #             user_english = changes["Target English Translation"].strip()
        #             if user_english:
        #                 if save_split_tokens(telugu_key, user_english, master_lexicon):
        #                     updated_counter += 1
        if critical_state or master_state:
            master_lexicon = load_lexicon()
            updated_counter = 0
            
            # Helper function to save both macro (full phrase) and micro (split words) mappings
            def save_dual_layer_tokens(telugu_phrase, english_phrase, lexicon_dict):
                has_updates = False
                
                # Layer 1: Save the complete macro mapping for instant O(1) full phrase cache hits
                if lexicon_dict.get(telugu_phrase) != english_phrase:
                    lexicon_dict[telugu_phrase] = english_phrase
                    has_updates = True
                
                # Layer 2: Break down into individual micro word pairs for granular dictionary training
                t_words = telugu_phrase.strip().split()
                e_words = english_phrase.strip().split()
                
                # Only split if word counts match 1-to-1 to avoid misaligning names
                if len(t_words) == len(e_words):
                    for tw, ew in zip(t_words, e_words):
                        if lexicon_dict.get(tw) != ew:
                            lexicon_dict[tw] = ew
                            has_updates = True
                            
                return has_updates

            # Apply dual-layer updates from Critical Data Editor Tab
            for row_idx_str, changes in critical_state.items():
                if "Suggested English Translation" in changes:
                    row_idx = int(row_idx_str)
                    telugu_key = df_audit.iloc[row_idx]["Original Telugu Input"]
                    user_english = changes["Suggested English Translation"].strip()
                    if user_english:
                        if save_dual_layer_tokens(telugu_key, user_english, master_lexicon):
                            updated_counter += 1

            # Apply dual-layer updates from Master Directory Data Editor Tab
            for row_idx_str, changes in master_state.items():
                if "Target English Translation" in changes:
                    row_idx = int(row_idx_str)
                    telugu_key = df_master.iloc[row_idx]["Original Telugu Input"]
                    user_english = changes["Target English Translation"].strip()
                    if user_english:
                        if save_dual_layer_tokens(telugu_key, user_english, master_lexicon):
                            updated_counter += 1
                            
            # if updated_counter > 0:
            #     save_lexicon(master_lexicon)
            #     st.sidebar.success(f"Successfully optimized storage with full phrase and token-split lookups!")
            #     trigger_reprocess = True
            if updated_counter > 0:
                save_lexicon(master_lexicon)
                st.sidebar.success(f"Successfully saved {updated_counter} manual alterations down to system cache storage!")
                trigger_reprocess = True

        # Re-run pipeline operations cleanly if updates were saved
        with st.spinner("Processing system updates stably..."):
            if trigger_reprocess:
                uploaded_file.seek(0)
                transactions, updated_flags, updated_master_map = parse_cash_workbook(uploaded_file, start_date_cutoff=st.session_state["saved_cutoff_date"])
                audit_report = run_cash_audit(transactions)
                
                st.session_state["raw_transactions"] = transactions
                st.session_state["report"] = audit_report
                st.session_state["flagged_names_map"] = updated_flags
                st.session_state["master_names_map"] = updated_master_map

            transactions = st.session_state["raw_transactions"]
            
            if is_ashramam:
                xml_text = generate_ashramam_tally_xml(transactions, cash_ledger=st.session_state["saved_bank_ledger"], donation_ledger=st.session_state["saved_suspense_ledger"])
                st.session_state["xlsx"] = build_nested_tally_sheets(transactions, cash_ledger=st.session_state["saved_bank_ledger"], donation_ledger=st.session_state["saved_suspense_ledger"])
            else:
                xml_text = generate_tally_xml(transactions, output_path=None, bank_ledger=st.session_state["saved_bank_ledger"], suspense_ledger=st.session_state["saved_suspense_ledger"], opening_balance=st.session_state["opening_balance"])
                validation_report = build_validation_report(st.session_state["sanitized_text"], transactions, xml_text, st.session_state["saved_bank_ledger"], st.session_state["saved_suspense_ledger"])
                
                temp_xlsx_path = os.path.join("temp_uploads", "audit_temp.xlsx")
                export_xml_audit_workbook(xml_text, temp_xlsx_path, bank_ledger=final_bank_ledger, suspense_ledger=final_suspense_ledger)
                with open(temp_xlsx_path, "rb") as f: xlsx_data = f.read()
                if os.path.exists(temp_xlsx_path): os.remove(temp_xlsx_path)
                
                st.session_state["report"] = validation_report
                st.session_state["xlsx"] = xlsx_data

            st.session_state["xml"] = xml_text
            st.session_state["files_ready"] = True
            
        st.rerun()

# -------------------------------------------------------------
# UNLOCKED DOWNLOAD PROVIDER PANEL
# -------------------------------------------------------------
if "files_ready" in st.session_state and "xml" in st.session_state:
    report = st.session_state["report"]
    is_ashramam = st.session_state.get("is_ashramam", False)
    
    st.divider()
    st.success("🎉 Target conversion and formatting outputs generated successfully!")
    
    col_xml, col_xlsx = st.columns(2)
    with col_xml:
        st.download_button(
            label="Download Tally Import XML File (.xml)",
            data=st.session_state["xml"],
            file_name="Ashramam_Cash_Receipts.xml" if is_ashramam else f"{bank_type[:3].upper()}_tally_import.xml",
            mime="application/xml",
            use_container_width=True
        )
    with col_xlsx:
        st.download_button(
            label="Download Ledger Sheets Preview Workbook (.xlsx)",
            data=st.session_state["xlsx"],
            file_name="Tally_Nested_Sheets_Preview.xlsx" if is_ashramam else "statement_audit_viewer.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # --- METRICS DISPLAY ---
    st.divider()
    if is_ashramam:
        st.subheader("📈 Summary Validation Checks")
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Total Translated Voucher Records", f"{report['total_count']:,}")
        with m2:
            st.metric("Total Money In / Cash Collected (Debit Sum)", f"₹ {report['total_debit']:,.2f}")
            
        df_months = pd.DataFrame(report["monthly_summaries"])
        st.subheader("📊 Month-by-Month Money Flow (Receipt Donations)")
        fig = px.bar(df_months, x="month_label", y="debit_total", labels={"month_label": "Month Timeline", "debit_total": "Donation Inflow (₹)"}, color_discrete_sequence=["#2ecc71"])
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📋 Monthly Balance Sheet Ledger Metrics")
        display_df = df_months[["month_label", "transaction_count", "debit_total"]].copy()
        display_df.columns = ["Month Timeline", "Transaction Count", "Total Receipts / Money In (₹)"]
        st.dataframe(display_df.style.format({"Total Receipts / Money In (₹)": "{:,.2f}"}), use_container_width=True, hide_index=True)
        
    else:
        stmt = report["statement"]
        xml_val = report["xml"]
        
        if stmt.get("audit_message"):
            st.warning(stmt["audit_message"])
            
        st.subheader("📈 Summary Validation Checks")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Transactions Processed", f"{stmt['transaction_count']:,}")
        with m2:
            st.metric("3-Check Summary Audit", "🟢 PASSED" if stmt["is_reconciled"] else "🔴 FAILED")
        with m3:
            st.metric("Row Count Alignment", "✅ MATCHED" if xml_val["voucher_count_matches"] else "❌ MISMATCH")
        with m4:
            st.metric("Voucher Amount Sum Match", "✅ MATCHED" if xml_val["voucher_amount_total_matches"] else "❌ MISMATCH")

        if "monthly_summaries" in stmt and stmt["monthly_summaries"]:
            df_months = pd.DataFrame(stmt["monthly_summaries"])
            df_melted = df_months.melt(id_vars=["month_label"], value_vars=["credit_total", "debit_total"], var_name="Transaction Category", value_name="Value Amount (INR)")
            df_melted["Transaction Category"] = df_melted["Transaction Category"].map({"credit_total": "Total Money Out (Payments Made)", "debit_total": "Total Money In (Receipts Received)"})

            st.subheader("📊 Month-by-Month Money Flow Comparison")
            fig = px.bar(df_melted, x="month_label", y="Value Amount (INR)", color="Transaction Category", barmode="group", labels={"month_label": "Month", "Value Amount (INR)": "Amount (₹)"}, color_discrete_sequence=["#e74c3c", "#2ecc71"])
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("📋 Monthly Balance Sheet Ledger Metrics")
            display_df = df_months[["month_label", "transaction_count", "opening_balance", "debit_total", "credit_total", "closing_balance", "is_reconciled"]].copy()
            display_df["is_reconciled"] = display_df["is_reconciled"].map({True: "🟢 RECONCILED", False: "🔴 ERROR"})
            display_df.columns = ["Month Timeline", "Transaction Count", "Opening Balance (₹)", "Total Receipts / In (₹)", "Total Payments / Out (₹)", "Closing Balance (₹)", "Audit Status"]
            st.dataframe(display_df.style.format({"Opening Balance (₹)": "{:,.2f}", "Total Receipts / In (₹)": "{:,.2f}", "Total Payments / Out (₹)": "{:,.2f}", "Closing Balance (₹)": "{:,.2f}"}), use_container_width=True, hide_index=True)


# # pages/workspace.py
# import streamlit as st
# import json
# import os
# import pandas as pd
# import plotly.express as px
# from datetime import datetime

# # Import banking core modules
# from services.pdf_reader import extract_text
# from services.statement_validator import build_validation_report
# from services.xml_generator import generate_tally_xml
# from services.xlsx_viewer import export_xml_audit_workbook

# # Import Ashramam Custom Modules
# from parsers.cash_parser import parse_cash_workbook, MAPPING_FILE, load_lexicon, save_lexicon
# from services.cash_validator import run_cash_audit
# from services.cash_xlsx_writer import build_nested_tally_sheets
# from services.cash_xml_generator import generate_ashramam_tally_xml

# st.set_page_config(page_title="Workspace | Tally Automation", layout="wide")

# if st.button("⬅️ Back to Information Page", type="secondary"):
#     st.switch_page("app.py")

# st.title("📊 Financial Statement to Tally XML Engine")
# st.markdown("Upload your bank statement file or multi-tab cash receipts workbook below.")

# os.makedirs("temp_uploads", exist_ok=True)

# # -------------------------------------------------------------
# # SIDEBAR CONTROLS
# # -------------------------------------------------------------
# st.sidebar.header("⚙️ Configuration Settings")

# bank_type = st.sidebar.selectbox(
#     "1. Select Statement Processing Type",
#     ["Bank of Baroda (BOB)", "State Bank of India (SBI)", "Ashramam Cash Receipts Ledger"]
# )

# if bank_type == "Ashramam Cash Receipts Ledger":
#     file_types = ["xlsx", "csv"]
#     help_msg = "Select a strict A,B,C,D,E format ledger workbook spreadsheet"
# else:
#     file_types = ["pdf"]
#     help_msg = "Select a digital bank e-statement document"

# uploaded_file = st.sidebar.file_uploader(
#     f"2. Upload Source File ({', '.join(file_types).upper()})", 
#     type=file_types,
#     help=help_msg
# )

# strategy_type = "Whole Document"
# boundary_date_input = None

# if bank_type != "Ashramam Cash Receipts Ledger":
#     strategy_type = st.sidebar.selectbox(
#         "3. Select Ingestion Strategy", 
#         ["Whole Document", "First Chunk", "Continuation Chunk"]
#     )
#     if strategy_type == "Continuation Chunk":
#         st.sidebar.markdown("📅 **Timeline Slicing Parameter**")
#         boundary_date_input = st.sidebar.date_input(
#             "Show transactions AFTER this date:",
#             value=datetime(2025, 4, 1)
#         )

# convert_btn = st.sidebar.button("Convert File Now", use_container_width=True, disabled=not uploaded_file)

# # -------------------------------------------------------------
# # STEP-BY-STEP CONVERSION PIPELINE
# # -------------------------------------------------------------
# if uploaded_file and convert_btn:
#     for key in ["xml", "report", "xlsx", "is_ashramam", "conversion_complete", "flagged_names_map"]:
#         if key in st.session_state: del st.session_state[key]

#     temp_file_path = os.path.join("temp_uploads", uploaded_file.name)
#     with open(temp_file_path, "wb") as f:
#         f.write(uploaded_file.getbuffer())
        
#     # --- BRANCH PATH A: EXCLUSIVE CASH LEDGER PIPELINE ---
#     if bank_type == "Ashramam Cash Receipts Ledger":
#         with st.status("🔮 Running Ashramam Ledger Pipeline...", expanded=True) as status_box:
#             try:
#                 st.write("⏳ Step 1: Running strict A,B,C,D,E verification guardrails...")
#                 transactions, flagged_map = parse_cash_workbook(uploaded_file) 
                
#                 st.write("⏳ Step 2: Running cash entry audit pipelines...")
#                 audit_report = run_cash_audit(transactions)
                
#                 st.write("⏳ Step 3: Generating multi-sheet Tally preview ledger...")
#                 excel_preview = build_nested_tally_sheets(transactions)
                
#                 st.session_state["raw_transactions"] = transactions
#                 st.session_state["report"] = audit_report
#                 st.session_state["xlsx"] = excel_preview
#                 st.session_state["flagged_names_map"] = flagged_map
#                 st.session_state["conversion_complete"] = True
#                 st.session_state["is_ashramam"] = True
                
#                 status_box.update(label="✅ Ashramam Processing Chain Complete!", state="complete")
#             except ValueError as val_err:
#                 status_box.update(label="❌ Strict Structural Validation Failed", state="error")
#                 st.error(str(val_err))
#                 st.stop()
#             except Exception as e:
#                 st.error(f"❌ Conversion System Failure: {str(e)}")
#                 status_box.update(label="❌ Conversion Error", state="error")
#             finally:
#                 if os.path.exists(temp_file_path): os.remove(temp_file_path)
                
#     # --- BRANCH PATH B: ORIGINAL BANKING STATEMENT PIPELINE ---
#     else:
#         is_profile_mismatch = False
#         with st.status("🛠️ Running Conversion Engine...", expanded=True) as status_box:
#             try:
#                 st.write("⏳ Step 1: Extracting text matrix layers from PDF source...")
#                 text = extract_text(temp_file_path)
                
#                 from parsers.router import verify_bank_profile, route_to_parser
#                 if not verify_bank_profile(bank_type, text):
#                     is_profile_mismatch = True
#                     status_box.update(label="❌ Bank Selection Mismatch", state="error")
#                 else:
#                     st.write(f"⏳ Step 2: Applying Ingestion Strategy: [{strategy_type}]...")
#                     from parsers.bob_parser import parse_opening_balance as parse_bob_opening
#                     from parsers.sbi_parser import parse_opening_balance as parse_sbi_opening
#                     from strategies import WholeChunk, FirstChunk, ContinuationChunk
                    
#                     parse_opening_func = parse_bob_opening if "BOB" in bank_type else parse_sbi_opening
                    
#                     if strategy_type == "Whole Document":
#                         sanitized_text, opening_bal = WholeChunk.process_strategy(text, parse_opening_func)
#                     elif strategy_type == "First Chunk":
#                         sanitized_text, opening_bal = FirstChunk.process_strategy(text, parse_opening_func)
#                     elif strategy_type == "Continuation Chunk":
#                         sanitized_text, opening_bal = ContinuationChunk.process_strategy(
#                             text, parse_opening_func, bank_type, boundary_date_input
#                         )

#                     st.write("⏳ Step 3: Extracting transaction records row-by-row...")
#                     transactions = route_to_parser(bank_type, sanitized_text)
                    
#                     st.session_state["raw_transactions"] = transactions
#                     st.session_state["sanitized_text"] = sanitized_text
#                     st.session_state["opening_balance"] = opening_bal
#                     st.session_state["conversion_complete"] = True
#                     st.session_state["is_ashramam"] = False
                    
#                     status_box.update(label="✅ Step-By-Step Data Extraction Complete!", state="complete")
#             except Exception as e:
#                 st.error(f"❌ Conversion Failed: {str(e)}")
#                 status_box.update(label="❌ Conversion Error", state="error")
#             finally:
#                 if os.path.exists(temp_file_path): os.remove(temp_file_path)

#         if is_profile_mismatch:
#             st.error(f"❌ **Bank Profile Mismatch!** PDF markers do not match selected bank profile.")
#             st.stop()

# # -------------------------------------------------------------
# # POST-CONVERSION LEDGER CONFIGURATION FOR DOWNLOADS
# # -------------------------------------------------------------
# if "conversion_complete" in st.session_state and "xml" not in st.session_state:
#     st.divider()
#     st.subheader("🎯 Final Step: Align with your Tally Ledger Name")
    
#     is_ashramam = st.session_state.get("is_ashramam", False)
    
#     if is_ashramam:
#         default_bank_suggestion = "Cash"
#         default_suspense_suggestion = "Annadana Prasadam Donations Received"
#     else:
#         default_bank_suggestion = "BANK OF BARODA" if "BOB" in bank_type else "STATE BANK OF INDIA"
#         default_suspense_suggestion = "Suspense"
        
#     col_input1, col_input2, col_action = st.columns([1.5, 1.5, 1])
#     with col_input1:
#         final_bank_ledger = st.text_input("Debit Ledger Name (Tally Cash/Bank Account):", value=default_bank_suggestion)
#     with col_input2:
#         final_suspense_ledger = st.text_input("Credit Ledger Name (Tally Particulars Account):", value=default_suspense_suggestion)
#     with col_action:
#         st.write(" ") 
#         generate_btn = st.button("Verify & Lock Ledger Name 🔒", type="primary", use_container_width=True)

#     if generate_btn:
#         transactions = st.session_state["raw_transactions"]
        
#         if is_ashramam:
#             xml_text = generate_ashramam_tally_xml(
#                 transactions, 
#                 cash_ledger=final_bank_ledger, 
#                 donation_ledger=final_suspense_ledger
#             )
#         else:
#             sanitized_text = st.session_state["sanitized_text"]
#             opening_bal = st.session_state["opening_balance"]
            
#             xml_text = generate_tally_xml(
#                 transactions, output_path=None, 
#                 bank_ledger=final_bank_ledger, suspense_ledger=final_suspense_ledger, 
#                 opening_balance=opening_bal
#             )
#             validation_report = build_validation_report(
#                 sanitized_text, transactions, xml_text, final_bank_ledger, final_suspense_ledger
#             )
            
#             temp_xlsx_path = os.path.join("temp_uploads", "audit_temp.xlsx")
#             export_xml_audit_workbook(xml_text, temp_xlsx_path, bank_ledger=final_bank_ledger, suspense_ledger=final_suspense_ledger)
#             with open(temp_xlsx_path, "rb") as f: xlsx_data = f.read()
#             if os.path.exists(temp_xlsx_path): os.remove(temp_xlsx_path)
            
#             st.session_state["report"] = validation_report
#             st.session_state["xlsx"] = xlsx_data

#         st.session_state["xml"] = xml_text
#         st.session_state["active_ledger"] = final_bank_ledger
#         st.rerun()

# # -------------------------------------------------------------
# # RESULTS DISPLAY & VISUALIZATION DASHBOARD
# # -------------------------------------------------------------
# if "xml" in st.session_state and "report" in st.session_state:
#     report = st.session_state["report"]
#     is_ashramam = st.session_state.get("is_ashramam", False)
#     flagged_names = st.session_state.get("flagged_names_map", {})
    
#     # -------------------------------------------------------------
#     # PARALLEL NAME AUDITING GUARDRAIL REGISTRY
#     # -------------------------------------------------------------
#     has_audit_flags = is_ashramam and len(flagged_names) > 0
#     allow_download_display = True
    
#     if has_audit_flags:
#         st.divider()
#         st.subheader(f"🔍 Name Verification Guardrail (Flagged Records: {len(flagged_names)})")
#         st.warning("Detected translated name outputs containing special accents or words exceeding 10 letters.")
        
#         bypass_choice = st.radio(
#             "Would you like to resolve the flags or bypass and download files directly?",
#             ["Correct Names (Recommended)", "Bypass Flags and Open Downloads Anyway"],
#             key="bypass_radio_toggle"
#         )
        
#         if bypass_choice == "Correct Names (Recommended)":
#             allow_download_display = False
#             st.info("💡 Double-click any cell inside the 'Corrected English Name' column to update spelling variants.")
            
#             # Pack map layers cleanly into a tabular matrix frame
#             audit_rows = [{"Original Telugu Input": k, "Corrected English Name": v} for k, v in flagged_names.items()]
#             df_audit = pd.DataFrame(audit_rows)
            
#             edited_df = st.data_editor(
#                 df_audit,
#                 use_container_width=True,
#                 disabled=["Original Telugu Input"],
#                 key="dictionary_live_editor"
#             )
            
#             save_mappings_btn = st.button("Commit Grid Corrections & Re-Process File 💾", type="primary")
            
#             if save_mappings_btn:
#                 master_lexicon = load_lexicon()
#                 updated_counter = 0
                
#                 for _, row in edited_df.iterrows():
#                     telugu_key = row["Original Telugu Input"]
#                     user_english = row["Corrected English Name"].strip()
                    
#                     if user_english and user_english != flagged_names[telugu_key]:
#                         master_lexicon[telugu_key] = user_english
#                         updated_counter += 1
                        
#                 if updated_counter > 0:
#                     save_lexicon(master_lexicon)
#                     st.success(f"Successfully synchronized {updated_counter} structural items directly to your mapping file!")
                    
#                     # Force clear processed cache layers to run pipeline verification loops
#                     for k in ["xml", "report", "xlsx", "flagged_names_map"]:
#                         if k in st.session_state: del st.session_state[k]
#                     st.rerun()
#                 else:
#                     st.warning("No spelling changes were recorded in the data grid.")

#     # -------------------------------------------------------------
#     # FILE DOWNLOAD PROVIDER ACTION PANEL
#     # -------------------------------------------------------------
#     if allow_download_display:
#         st.success("🎉 Target structural validation parameters complete!")
#         col_xml, col_xlsx = st.columns(2)
#         with col_xml:
#             st.download_button(
#                 label="Download Tally Import XML File (.xml)",
#                 data=st.session_state["xml"],
#                 file_name="Ashramam_Cash_Receipts.xml" if is_ashramam else f"{bank_type[:3].upper()}_tally_import.xml",
#                 mime="application/xml",
#                 use_container_width=True
#             )
#         with col_xlsx:
#             st.download_button(
#                 label="Download Ledger Sheets Preview Workbook (.xlsx)",
#                 data=st.session_state["xlsx"],
#                 file_name="Tally_Nested_Sheets_Preview.xlsx" if is_ashramam else "statement_audit_viewer.xlsx",
#                 mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                 use_container_width=True
#             )

#     # -------------------------------------------------------------
#     # DATA ANALYTICS & VISUALIZATION INFRASTRUCTURE (ALWAYS UNLOCKED)
#     # -------------------------------------------------------------
#     st.divider()

#     if is_ashramam:
#         # --- PATHWAY A: EXCLUSIVE SINGLE-SIDED DEBIT CASH METRICS ---
#         st.subheader("📈 Summary Validation Checks")
#         m1, m2 = st.columns(2)
#         with m1:
#             st.metric("Total Translated Voucher Records", f"{report['total_count']:,}")
#         with m2:
#             st.metric("Total Money In / Cash Collected (Debit Sum)", f"₹ {report['total_debit']:,.2f}")
            
#         if report["duplicates"]:
#             st.warning(f"⚠️ Flagged {len(report['duplicates'])} duplicate receipt numbers in rows: {report['duplicates']}")
            
#         df_months = pd.DataFrame(report["monthly_summaries"])
        
#         st.subheader("📊 Month-by-Month Money Flow (Receipt Donations)")
#         fig = px.bar(
#             df_months, x="month_label", y="debit_total",
#             labels={"month_label": "Month Timeline", "debit_total": "Donation Inflow (₹)"},
#             color_discrete_sequence=["#2ecc71"]
#         )
#         st.plotly_chart(fig, use_container_width=True)
        
#         st.subheader("📋 Monthly Balance Sheet Ledger Metrics")
#         display_df = df_months[["month_label", "transaction_count", "debit_total"]].copy()
#         display_df.columns = ["Month Timeline", "Transaction Count", "Total Receipts / Money In (₹)"]
#         st.dataframe(display_df.style.format({"Total Receipts / Money In (₹)": "{:,.2f}"}), use_container_width=True, hide_index=True)
        
#     else:
#         # --- PATHWAY B: ORIGINAL DOUBLE-ENTRY BANKING METRICS ---
#         stmt = report["statement"]
#         xml_val = report["xml"]
        
#         st.subheader("📈 Summary Validation Checks")
#         m1, m2, m3, m4 = st.columns(4)
#         with m1:
#             st.metric("Total Transactions Processed", f"{stmt['transaction_count']:,}")
#         with m2:
#             st.metric("3-Check Summary Audit", "🟢 PASSED" if stmt["is_reconciled"] else "🔴 FAILED")
#         with m3:
#             st.metric("Row Count Alignment", "✅ MATCHED" if xml_val["voucher_count_matches"] else "❌ MISMATCH")
#         with m4:
#             st.metric("Voucher Amount Sum Match", "✅ MATCHED" if xml_val["voucher_amount_total_matches"] else "❌ MISMATCH")

#         if "monthly_summaries" in stmt and stmt["monthly_summaries"]:
#             df_months = pd.DataFrame(stmt["monthly_summaries"])
#             df_melted = df_months.melt(id_vars=["month_label"], value_vars=["credit_total", "debit_total"], var_name="Transaction Category", value_name="Value Amount (INR)")
#             df_melted["Transaction Category"] = df_melted["Transaction Category"].map({"credit_total": "Total Money Out (Payments Made)", "debit_total": "Total Money In (Receipts Received)"})

#             st.subheader("📊 Month-by-Month Money Flow Comparison")
#             fig = px.bar(df_melted, x="month_label", y="Value Amount (INR)", color="Transaction Category", barmode="group", labels={"month_label": "Month", "Value Amount (INR)": "Amount (₹)"}, color_discrete_sequence=["#e74c3c", "#2ecc71"])
#             st.plotly_chart(fig, use_container_width=True)

#             st.subheader("📋 Monthly Balance Sheet Ledger Metrics")
#             display_df = df_months[["month_label", "transaction_count", "opening_balance", "debit_total", "credit_total", "closing_balance", "is_reconciled"]].copy()
#             display_df["is_reconciled"] = display_df["is_reconciled"].map({True: "🟢 RECONCILED", False: "🔴 ERROR"})
#             display_df.columns = ["Month Timeline", "Transaction Count", "Opening Balance (₹)", "Total Receipts / In (₹)", "Total Payments / Out (₹)", "Closing Balance (₹)", "Audit Status"]
#             st.dataframe(display_df.style.format({"Opening Balance (₹)": "{:,.2f}", "Total Receipts / In (₹)": "{:,.2f}", "Total Payments / Out (₹)": "{:,.2f}", "Closing Balance (₹)": "{:,.2f}"}), use_container_width=True, hide_index=True)

# # pages/workspace.py
# import streamlit as st
# import json
# import os
# import pandas as pd
# import plotly.express as px
# from datetime import datetime

# # Import banking core modules
# from services.pdf_reader import extract_text
# from services.statement_validator import build_validation_report
# from services.xml_generator import generate_tally_xml
# from services.xlsx_viewer import export_xml_audit_workbook

# # Import Ashramam Custom Modules
# from parsers.cash_parser import parse_cash_workbook
# from services.cash_validator import run_cash_audit
# from services.cash_xlsx_writer import build_nested_tally_sheets
# from services.cash_xml_generator import generate_ashramam_tally_xml

# st.set_page_config(page_title="Workspace | Tally Automation", layout="wide")

# if st.button("⬅️ Back to Information Page", type="secondary"):
#     st.switch_page("app.py")

# st.title("📊 Financial Statement to Tally XML Engine")
# st.markdown("Upload your bank statement file or multi-tab cash receipts workbook below.")

# os.makedirs("temp_uploads", exist_ok=True)

# # -------------------------------------------------------------
# # SIDEBAR CONTROLS
# # -------------------------------------------------------------
# st.sidebar.header("⚙️ Configuration Settings")

# bank_type = st.sidebar.selectbox(
#     "1. Select Statement Processing Type",
#     ["Bank of Baroda (BOB)", "State Bank of India (SBI)", "Ashramam Cash Receipts Ledger"]
# )

# if bank_type == "Ashramam Cash Receipts Ledger":
#     file_types = ["xlsx", "csv"]
#     help_msg = "Select a strict A,B,C,D,E format ledger workbook spreadsheet"
# else:
#     file_types = ["pdf"]
#     help_msg = "Select a digital bank e-statement document"

# uploaded_file = st.sidebar.file_uploader(
#     f"2. Upload Source File ({', '.join(file_types).upper()})", 
#     type=file_types,
#     help=help_msg
# )

# strategy_type = "Whole Document"
# boundary_date_input = None

# if bank_type != "Ashramam Cash Receipts Ledger":
#     strategy_type = st.sidebar.selectbox(
#         "3. Select Ingestion Strategy", 
#         ["Whole Document", "First Chunk", "Continuation Chunk"]
#     )
#     if strategy_type == "Continuation Chunk":
#         st.sidebar.markdown("📅 **Timeline Slicing Parameter**")
#         boundary_date_input = st.sidebar.date_input(
#             "Show transactions AFTER this date:",
#             value=datetime(2025, 4, 1)
#         )

# convert_btn = st.sidebar.button("Convert File Now", use_container_width=True, disabled=not uploaded_file)

# # -------------------------------------------------------------
# # STEP-BY-STEP CONVERSION PIPELINE
# # -------------------------------------------------------------
# if uploaded_file and convert_btn:
#     for key in ["xml", "report", "xlsx", "is_ashramam", "conversion_complete"]:
#         if key in st.session_state: del st.session_state[key]

#     temp_file_path = os.path.join("temp_uploads", uploaded_file.name)
#     with open(temp_file_path, "wb") as f:
#         f.write(uploaded_file.getbuffer())
        
#     # --- BRANCH PATH A: EXCLUSIVE CASH LEDGER PIPELINE ---
#     if bank_type == "Ashramam Cash Receipts Ledger":
#         with st.status("🔮 Running Ashramam Ledger Pipeline...", expanded=True) as status_box:
#             try:
#                 st.write("⏳ Step 1: Running strict A,B,C,D,E verification guardrails...")
#                 transactions = parse_cash_workbook(uploaded_file) 
                
#                 st.write("⏳ Step 2: Running cash entry audit pipelines...")
#                 audit_report = run_cash_audit(transactions)
                
#                 st.write("⏳ Step 3: Generating multi-sheet Tally preview ledger...")
#                 excel_preview = build_nested_tally_sheets(transactions)
                
#                 st.session_state["raw_transactions"] = transactions
#                 st.session_state["report"] = audit_report
#                 st.session_state["xlsx"] = excel_preview
#                 st.session_state["conversion_complete"] = True
#                 st.session_state["is_ashramam"] = True
                
#                 status_box.update(label="✅ Ashramam Processing Chain Complete!", state="complete")
#             except ValueError as val_err:
#                 # Intercept strict formatting constraint exceptions and block execution instantly
#                 status_box.update(label="❌ Strict Structural Validation Failed", state="error")
#                 st.error(str(val_err))
#                 st.stop()
#             except Exception as e:
#                 st.error(f"❌ Conversion System Failure: {str(e)}")
#                 status_box.update(label="❌ Conversion Error", state="error")
#             finally:
#                 if os.path.exists(temp_file_path): os.remove(temp_file_path)
                
#     # --- BRANCH PATH B: ORIGINAL BANKING STATEMENT PIPELINE (UNCHANGED) ---
#     else:
#         is_profile_mismatch = False
#         with st.status("🛠️ Running Conversion Engine...", expanded=True) as status_box:
#             try:
#                 st.write("⏳ Step 1: Extracting text matrix layers from PDF source...")
#                 text = extract_text(temp_file_path)
                
#                 from parsers.router import verify_bank_profile, route_to_parser
#                 if not verify_bank_profile(bank_type, text):
#                     is_profile_mismatch = True
#                     status_box.update(label="❌ Bank Selection Mismatch", state="error")
#                 else:
#                     st.write(f"⏳ Step 2: Applying Ingestion Strategy: [{strategy_type}]...")
#                     from parsers.bob_parser import parse_opening_balance as parse_bob_opening
#                     from parsers.sbi_parser import parse_opening_balance as parse_sbi_opening
#                     from strategies import WholeChunk, FirstChunk, ContinuationChunk
                    
#                     parse_opening_func = parse_bob_opening if "BOB" in bank_type else parse_sbi_opening
                    
#                     if strategy_type == "Whole Document":
#                         sanitized_text, opening_bal = WholeChunk.process_strategy(text, parse_opening_func)
#                     elif strategy_type == "First Chunk":
#                         sanitized_text, opening_bal = FirstChunk.process_strategy(text, parse_opening_func)
#                     elif strategy_type == "Continuation Chunk":
#                         sanitized_text, opening_bal = ContinuationChunk.process_strategy(
#                             text, parse_opening_func, bank_type, boundary_date_input
#                         )

#                     st.write("⏳ Step 3: Extracting transaction records row-by-row...")
#                     transactions = route_to_parser(bank_type, sanitized_text)
                    
#                     st.session_state["raw_transactions"] = transactions
#                     st.session_state["sanitized_text"] = sanitized_text
#                     st.session_state["opening_balance"] = opening_bal
#                     st.session_state["conversion_complete"] = True
#                     st.session_state["is_ashramam"] = False
                    
#                     status_box.update(label="✅ Step-By-Step Data Extraction Complete!", state="complete")
#             except Exception as e:
#                 st.error(f"❌ Conversion Failed: {str(e)}")
#                 status_box.update(label="❌ Conversion Error", state="error")
#             finally:
#                 if os.path.exists(temp_file_path): os.remove(temp_file_path)

#         if is_profile_mismatch:
#             st.error(f"❌ **Bank Profile Mismatch!** PDF markers do not match selected bank profile.")
#             st.stop()

# # -------------------------------------------------------------
# # POST-CONVERSION LEDGER CONFIGURATION FOR DOWNLOADS
# # -------------------------------------------------------------
# if "conversion_complete" in st.session_state and "xml" not in st.session_state:
#     st.divider()
#     st.subheader("🎯 Final Step: Align with your Tally Ledger Name")
    
#     is_ashramam = st.session_state.get("is_ashramam", False)
    
#     if is_ashramam:
#         default_bank_suggestion = "Cash"
#         default_suspense_suggestion = "Annadana Prasadam Donations Received"
#     else:
#         default_bank_suggestion = "BANK OF BARODA" if "BOB" in bank_type else "STATE BANK OF INDIA"
#         default_suspense_suggestion = "Suspense"
        
#     col_input1, col_input2, col_action = st.columns([1.5, 1.5, 1])
#     with col_input1:
#         final_bank_ledger = st.text_input("Debit Ledger Name (Tally Cash/Bank Account):", value=default_bank_suggestion)
#     with col_input2:
#         final_suspense_ledger = st.text_input("Credit Ledger Name (Tally Particulars Account):", value=default_suspense_suggestion)
#     with col_action:
#         st.write(" ") 
#         generate_btn = st.button("Verify & Lock Ledger Name 🔒", type="primary", use_container_width=True)

#     if generate_btn:
#         transactions = st.session_state["raw_transactions"]
        
#         if is_ashramam:
#             xml_text = generate_ashramam_tally_xml(
#                 transactions, 
#                 cash_ledger=final_bank_ledger, 
#                 donation_ledger=final_suspense_ledger
#             )
#         else:
#             sanitized_text = st.session_state["sanitized_text"]
#             opening_bal = st.session_state["opening_balance"]
            
#             xml_text = generate_tally_xml(
#                 transactions, output_path=None, 
#                 bank_ledger=final_bank_ledger, suspense_ledger=final_suspense_ledger, 
#                 opening_balance=opening_bal
#             )
#             validation_report = build_validation_report(
#                 sanitized_text, transactions, xml_text, final_bank_ledger, final_suspense_ledger
#             )
            
#             temp_xlsx_path = os.path.join("temp_uploads", "audit_temp.xlsx")
#             export_xml_audit_workbook(xml_text, temp_xlsx_path, bank_ledger=final_bank_ledger, suspense_ledger=final_suspense_ledger)
#             with open(temp_xlsx_path, "rb") as f: xlsx_data = f.read()
#             if os.path.exists(temp_xlsx_path): os.remove(temp_xlsx_path)
            
#             st.session_state["report"] = validation_report
#             st.session_state["xlsx"] = xlsx_data

#         st.session_state["xml"] = xml_text
#         st.session_state["active_ledger"] = final_bank_ledger
#         st.rerun()

# # -------------------------------------------------------------
# # RESULTS DISPLAY & VISUALIZATION DASHBOARD
# # -------------------------------------------------------------
# if "xml" in st.session_state and "report" in st.session_state:
#     report = st.session_state["report"]
#     is_ashramam = st.session_state.get("is_ashramam", False)
    
#     st.success("🎉 Target structural validation parameters complete!")
    
#     col_xml, col_xlsx = st.columns(2)
#     with col_xml:
#         st.download_button(
#             label="Download Tally Import XML File (.xml)",
#             data=st.session_state["xml"],
#             file_name="Ashramam_Cash_Receipts.xml" if is_ashramam else f"{bank_type[:3].upper()}_tally_import.xml",
#             mime="application/xml",
#             use_container_width=True
#         )
#     with col_xlsx:
#         st.download_button(
#             label="Download Ledger Sheets Preview Workbook (.xlsx)",
#             data=st.session_state["xlsx"],
#             file_name="Tally_Nested_Sheets_Preview.xlsx" if is_ashramam else "statement_audit_viewer.xlsx",
#             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#             use_container_width=True
#         )

#     st.divider()

#     if is_ashramam:
#         # --- PATHWAY A: EXCLUSIVE SINGLE-SIDED DEBIT CASH METRICS ---
#         st.subheader("📈 Summary Validation Checks")
#         m1, m2 = st.columns(2)
#         with m1:
#             st.metric("Total Translated Voucher Records", f"{report['total_count']:,}")
#         with m2:
#             st.metric("Total Money In / Cash Collected (Debit Sum)", f"₹ {report['total_debit']:,.2f}")
            
#         if report["duplicates"]:
#             st.warning(f"⚠️ Flagged {len(report['duplicates'])} duplicate receipt numbers in rows: {report['duplicates']}")
            
#         df_months = pd.DataFrame(report["monthly_summaries"])
        
#         st.subheader("📊 Month-by-Month Money Flow (Receipt Donations)")
#         fig = px.bar(
#             df_months, x="month_label", y="debit_total",
#             labels={"month_label": "Month Timeline", "debit_total": "Donation Inflow (₹)"},
#             color_discrete_sequence=["#2ecc71"]
#         )
#         st.plotly_chart(fig, use_container_width=True)
        
#         st.subheader("📋 Monthly Balance Sheet Ledger Metrics")
#         display_df = df_months[["month_label", "transaction_count", "debit_total"]].copy()
#         display_df.columns = ["Month Timeline", "Transaction Count", "Total Receipts / Money In (₹)"]
#         st.dataframe(display_df.style.format({"Total Receipts / Money In (₹)": "{:,.2f}"}), use_container_width=True, hide_index=True)
        
#     else:
#         # --- PATHWAY B: ORIGINAL DOUBLE-ENTRY BANKING METRICS ---
#         stmt = report["statement"]
#         xml_val = report["xml"]
        
#         st.subheader("📈 Summary Validation Checks")
#         m1, m2, m3, m4 = st.columns(4)
#         with m1:
#             st.metric("Total Transactions Processed", f"{stmt['transaction_count']:,}")
#         with m2:
#             st.metric("3-Check Summary Audit", "🟢 PASSED" if stmt["is_reconciled"] else "🔴 FAILED")
#         with m3:
#             st.metric("Row Count Alignment", "✅ MATCHED" if xml_val["voucher_count_matches"] else "❌ MISMATCH")
#         with m4:
#             st.metric("Voucher Amount Sum Match", "✅ MATCHED" if xml_val["voucher_amount_total_matches"] else "❌ MISMATCH")

#         if "monthly_summaries" in stmt and stmt["monthly_summaries"]:
#             df_months = pd.DataFrame(stmt["monthly_summaries"])
#             df_melted = df_months.melt(id_vars=["month_label"], value_vars=["credit_total", "debit_total"], var_name="Transaction Category", value_name="Value Amount (INR)")
#             df_melted["Transaction Category"] = df_melted["Transaction Category"].map({"credit_total": "Total Money Out (Payments Made)", "debit_total": "Total Money In (Receipts Received)"})

#             st.subheader("📊 Month-by-Month Money Flow Comparison")
#             fig = px.bar(df_melted, x="month_label", y="Value Amount (INR)", color="Transaction Category", barmode="group", labels={"month_label": "Month", "Value Amount (INR)": "Amount (₹)"}, color_discrete_sequence=["#e74c3c", "#2ecc71"])
#             st.plotly_chart(fig, use_container_width=True)

#             st.subheader("📋 Monthly Balance Sheet Ledger Metrics")
#             display_df = df_months[["month_label", "transaction_count", "opening_balance", "debit_total", "credit_total", "closing_balance", "is_reconciled"]].copy()
#             display_df["is_reconciled"] = display_df["is_reconciled"].map({True: "🟢 RECONCILED", False: "🔴 ERROR"})
#             display_df.columns = ["Month Timeline", "Transaction Count", "Opening Balance (₹)", "Total Receipts / In (₹)", "Total Payments / Out (₹)", "Closing Balance (₹)", "Audit Status"]
#             st.dataframe(display_df.style.format({"Opening Balance (₹)": "{:,.2f}", "Total Receipts / In (₹)": "{:,.2f}", "Total Payments / Out (₹)": "{:,.2f}", "Closing Balance (₹)": "{:,.2f}"}), use_container_width=True, hide_index=True)
            
            
            
# import streamlit as st
# import json
# import os
# import time
# import pandas as pd
# import plotly.express as px
# from datetime import datetime

# # Import pipeline core services
# from services.pdf_reader import extract_text
# from services.statement_validator import build_validation_report
# from services.xml_generator import generate_tally_xml
# from services.xlsx_viewer import export_xml_audit_workbook

# # Import routing and strategy scripts
# from parsers.router import verify_bank_profile, route_to_parser
# from parsers.bob_parser import parse_opening_balance as parse_bob_opening
# from parsers.sbi_parser import parse_opening_balance as parse_sbi_opening
# from strategies import WholeChunk, FirstChunk, ContinuationChunk

# st.set_page_config(page_title="Workspace | Tally Automation", layout="wide")

# if st.button("⬅️ Back to Information Page", type="secondary"):
#     st.switch_page("app.py")

# st.title("📊 Bank Statement to Tally XML Converter")
# st.markdown("Upload your bank e-statement PDF below to generate your Tally files.")

# os.makedirs("temp_uploads", exist_ok=True)

# # -------------------------------------------------------------
# # SIDEBAR CONTROLS
# # -------------------------------------------------------------
# st.sidebar.header("⚙️ Configuration Settings")

# uploaded_file = st.sidebar.file_uploader("1. Choose a Bank Statement (PDF format)", type=["pdf"])

# bank_type = st.sidebar.selectbox("2. Select Statement Processing Type",
#                                   ["Bank of Baroda (BOB)", "State Bank of India (SBI)", "Ashramam Cash Receipts Ledger"]
#                                 )

# strategy_type = st.sidebar.selectbox(
#     "3. Select Ingestion Strategy", 
#     ["Whole Document", "First Chunk", "Continuation Chunk"]
# )

# # Render interactive calendar dropdown only when needed
# boundary_date_input = None
# if strategy_type == "Continuation Chunk":
#     st.sidebar.markdown("📅 **Timeline Slicing Parameter**")
#     boundary_date_input = st.sidebar.date_input(
#         "Show transactions AFTER this date:",
#         value=datetime(2025, 4, 1),
#         help="Transactions on or before this day will be sliced out to avoid Tally duplicates."
#     )

# SUSPENSE_LEDGER = "Suspense"
# convert_btn = st.sidebar.button("Convert File Now", use_container_width=True, disabled=not uploaded_file)

# # -------------------------------------------------------------
# # STEP-BY-STEP CONVERSION PIPELINE
# # -------------------------------------------------------------
# if uploaded_file and convert_btn:
#     is_profile_mismatch = False
    
#     if strategy_type == "Continuation Chunk" and not boundary_date_input:
#         st.error("❌ Please specify a valid boundary target date cut-off inside the sidebar.")
#         st.stop()
        
#     temp_pdf_path = os.path.join("temp_uploads", uploaded_file.name)
#     with open(temp_pdf_path, "wb") as f:
#         f.write(uploaded_file.getbuffer())
        
#     with st.status("🛠️ Running Conversion Engine...", expanded=True) as status_box:
#         try:
#             st.write("⏳ Step 1: Extracting digital text matrix layers from PDF source...")
#             text = extract_text(temp_pdf_path)
            
#             if not verify_bank_profile(bank_type, text):
#                 is_profile_mismatch = True
#                 status_box.update(label="❌ Bank Selection Mismatch", state="error")
#             else:
#                 st.write(f"⏳ Step 2: Applying Ingestion Strategy: [{strategy_type}]...")
#                 parse_opening_func = parse_bob_opening if "BOB" in bank_type else parse_sbi_opening
                
#                 # Clean, modulated strategy handoffs
#                 if strategy_type == "Whole Document":
#                     sanitized_text, opening_bal = WholeChunk.process_strategy(text, parse_opening_func)
#                 elif strategy_type == "First Chunk":
#                     sanitized_text, opening_bal = FirstChunk.process_strategy(text, parse_opening_func)
#                 elif strategy_type == "Continuation Chunk":
#                     sanitized_text, opening_bal = ContinuationChunk.process_strategy(
#                         text, parse_opening_func, bank_type, boundary_date_input
#                     )

#                 st.write("⏳ Step 3: Extracting transaction records row-by-row...")
#                 transactions = route_to_parser(bank_type, sanitized_text)
                
#                 # Clear out stale runs to force rendering engine updates
#                 if "xml" in st.session_state: del st.session_state["xml"]
#                 if "report" in st.session_state: del st.session_state["report"]
                
#                 st.session_state["raw_transactions"] = transactions
#                 st.session_state["sanitized_text"] = sanitized_text
#                 st.session_state["opening_balance"] = opening_bal
#                 st.session_state["conversion_complete"] = True
                
#                 status_box.update(label="✅ Step-By-Step Data Extraction Complete!", state="complete")

#         except Exception as e:
#             st.error(f"❌ Conversion Failed: {str(e)}")
#             status_box.update(label="❌ Conversion Error", state="error")
#         finally:
#             if os.path.exists(temp_pdf_path): 
#                 os.remove(temp_pdf_path)

#     if is_profile_mismatch:
#         st.error(f"❌ **Bank Profile Mismatch!** PDF layout markers do not match chosen profile.")
#         st.stop()

# # -------------------------------------------------------------
# # POST-CONVERSION LEDGER CONFIGURATION FOR DOWNLOADS
# # -------------------------------------------------------------
# if "conversion_complete" in st.session_state:
#     st.divider()
#     st.subheader("🎯 Final Step: Align with your Tally Ledger Name")
    
#     default_ledger_suggestion = "BANK OF BARODA" if "BOB" in bank_type else "STATE BANK OF INDIA"
    
#     col_input, col_action = st.columns([2, 1])
#     with col_input:
#         final_bank_ledger = st.text_input(
#             "Enter the EXACT name of the Bank Ledger as written in your Tally Prime account:",
#             value=default_ledger_suggestion,
#             key="final_tally_ledger_input"
#         )
#     with col_action:
#         st.write(" ") 
#         generate_btn = st.button("Verify & Lock Ledger Name 🔒", type="primary", use_container_width=True)

#     if generate_btn or "xml" in st.session_state:
#         transactions = st.session_state["raw_transactions"]
#         sanitized_text = st.session_state["sanitized_text"]
#         opening_bal = st.session_state["opening_balance"]
        
#         xml_text = generate_tally_xml(
#             transactions,
#             output_path=None,
#             bank_ledger=final_bank_ledger,
#             suspense_ledger=SUSPENSE_LEDGER,
#             opening_balance=opening_bal
#         )
        
#         validation_report = build_validation_report(
#             sanitized_text, transactions, xml_text, final_bank_ledger, SUSPENSE_LEDGER
#         )
        
#         temp_xlsx_path = os.path.join("temp_uploads", "audit_temp.xlsx")
#         export_xml_audit_workbook(
#             xml_text, temp_xlsx_path, bank_ledger=final_bank_ledger, suspense_ledger=SUSPENSE_LEDGER
#         )
#         with open(temp_xlsx_path, "rb") as f:
#             xlsx_data = f.read()
#         if os.path.exists(temp_xlsx_path): 
#             os.remove(temp_xlsx_path)

#         st.session_state["report"] = validation_report
#         st.session_state["xml"] = xml_text
#         st.session_state["xlsx"] = xlsx_data
#         st.session_state["active_ledger"] = final_bank_ledger

# # -------------------------------------------------------------
# # RESTORED RESULTS & VISUALIZATION DASHBOARD
# # -------------------------------------------------------------
# if "xml" in st.session_state and "report" in st.session_state:
#     report = st.session_state["report"]
#     stmt = report["statement"]
#     xml_val = report["xml"]
    
#     st.success(f"🎉 Locked onto Tally Ledger target: **'{st.session_state['active_ledger']}'**!")
    
#     # --- DOWNLOAD ACTION SECTION ---
#     col_xml, col_xlsx, col_json = st.columns(3)
#     with col_xml:
#         st.download_button(
#             label="Download Tally XML File (.xml)",
#             data=st.session_state["xml"],
#             file_name=f"{bank_type[:3].upper()}_tally_import.xml",
#             mime="application/xml",
#             use_container_width=True
#         )
#     with col_xlsx:
#         st.download_button(
#             label="Download Excel View File (.xlsx)",
#             data=st.session_state["xlsx"],
#             file_name="statement_audit_viewer.xlsx",
#             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#             use_container_width=True
#         )
#     with col_json:
#         st.download_button(
#             label="Download Diagnostic Report (.json)",
#             data=json.dumps(report, indent=2),
#             file_name="validation_report.json",
#             mime="application/json",
#             use_container_width=True
#         )

#     st.divider()

#     # --- SUMMARY METRICS CARDS ---
#     st.subheader("📈 Summary Validation Checks")
#     m1, m2, m3, m4 = st.columns(4)
#     with m1:
#         st.metric("Total Transactions Processed", f"{stmt['transaction_count']:,}")
#     with m2:
#         status = "🟢 PASSED" if stmt["is_reconciled"] else "🔴 FAILED"
#         st.metric("3-Check Summary Audit", status)
#     with m3:
#         xml_match = "✅ MATCHED" if xml_val["voucher_count_matches"] else "❌ MISMATCH"
#         st.metric("Row Count Alignment", xml_match)
#     with m4:
#         st.metric("Voucher Amount Sum Match", "✅ MATCHED" if xml_val["voucher_amount_total_matches"] else "❌ MISMATCH")

#     # --- RESTORED DYNAMIC PLOTLY CHART ---
#     if "monthly_summaries" in stmt and stmt["monthly_summaries"]:
#         st.subheader("📊 Month-by-Month Money Flow Comparison")
#         df_months = pd.DataFrame(stmt["monthly_summaries"])
        
#         # Reshape data cleanly for dual grouping bars
#         df_melted = df_months.melt(
#             id_vars=["month_label"], 
#             value_vars=["credit_total", "debit_total"],
#             var_name="Transaction Category", 
#             value_name="Value Amount (INR)"
#         )
#         df_melted["Transaction Category"] = df_melted["Transaction Category"].map(
#             {"credit_total": "Total Money Out (Payments Made)", "debit_total": "Total Money In (Receipts Received)"}
#         )

#         fig = px.bar(
#             df_melted, 
#             x="month_label", 
#             y="Value Amount (INR)", 
#             color="Transaction Category",
#             barmode="group",
#             labels={"month_label": "Month", "Value Amount (INR)": "Amount (₹)"},
#             color_discrete_sequence=["#e74c3c", "#2ecc71"] # Outgoing = Red, Incoming = Green
#         )
#         st.plotly_chart(fig, use_container_width=True)

#         # --- RESTORED ACCOUNTING DATA BREAKDOWN TABLE ---
#         st.subheader("📋 Monthly Balance Sheet Ledger Metrics")
        
#         display_df = df_months[[
#             "month_label", "transaction_count", "opening_balance", 
#             "debit_total", "credit_total", "closing_balance", "is_reconciled"
#         ]].copy()
        
#         display_df["is_reconciled"] = display_df["is_reconciled"].map({
#             True: "🟢 RECONCILED",
#             False: "🔴 ERROR"
#         })
        
#         display_df.columns = [
#             "Month Timeline", "Transaction Count", "Opening Balance (₹)", 
#             "Total Receipts / In (₹)", "Total Payments / Out (₹)", "Closing Balance (₹)", "Audit Status"
#         ]
        
#         st.dataframe(
#             display_df.style.format({
#                 "Opening Balance (₹)": "{:,.2f}",
#                 "Total Receipts / In (₹)": "{:,.2f}",
#                 "Total Payments / Out (₹)": "{:,.2f}",
#                 "Closing Balance (₹)": "{:,.2f}"
#             }),
#             use_container_width=True,
#             hide_index=True
#         )

