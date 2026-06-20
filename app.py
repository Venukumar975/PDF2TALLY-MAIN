import streamlit as st

st.set_page_config(page_title="Tally Automation Suite", layout="wide")

st.title("🛡️ Errorless Conversion & Validation Architecture")
st.subheader("Automated Bank Statement to Tally XML Processing Engine")

st.divider()

col_main, col_nav = st.columns([2.5, 1])

with col_main:
    st.markdown("### 🔍 Why Can You Trust This App?")
    st.markdown(
        """
        Most generic conversion tools try to 'read' bank statements using unpredictable OCR scanning. 
        This application bypasses visual guessing entirely and guarantees structurally sound data mapping using a clear, **3-Check Verification Blueprint**:
        """
    )
    
    with st.expander("1. High-Level Summary Match (PDF Data Structure vs. XML Data Structure)", expanded=True):
        st.markdown(
            """
            * **How it works:** The engine scans both files as separate black boxes, compiling independent monthly analysis profiles.
            * **The Mirror Check:** It ensures that overall transaction counts, voucher numbers, and cumulative monthly sums perfectly align between the bank sheet and the generated code.
            """
        )

    with st.expander("2. Parallel Row-by-Row Line Verification", expanded=True):
        st.markdown(
            """
            * **How it works:** The auditor steps sequentially down both documents simultaneously, matching row $N$ in the statement directly to voucher $N$ inside the XML file.
            * **The Mirror Check:** It verifies line-by-line that date stamps are exact, transaction amounts match down to the paisa, and direction profiles correspond cleanly (PDF Deposit = XML Debit Receipt, PDF Withdrawal = XML Credit Payment).
            """
        )

    with st.expander("3. Sequence Integrity & Gap Verification", expanded=True):
        st.markdown(
            """
            * **How it works:** It scans the generated ledger numbers inside the underlying file structures.
            * **The Mirror Check:** It actively confirms that the index sequence never builds a duplicate ID that would overwrite data in Tally, and that no sequence gaps or line skips exist in the batch.
            """
        )

    st.markdown("### 📋 Supported Document Formats")
    st.info(
        "💡 **Compatible Profiles:** Works out-of-the-box with digitally generated, official bank e-statements from both Bank of Baroda (BOB) and State Bank of India (SBI). "
        "It **cannot** read photocopies or mobile phone scans, as those files lack an underlying digital text layer."
    )

with col_nav:
    st.markdown("### 🕹️ Navigation Menu")
    st.write("Ready to transform your statement files into production-ready accounting modules?")
    
    if st.button("Proceed to Workspace ➡️", type="primary", use_container_width=True, key="nav_to_workspace"):
        st.switch_page("pages/workspace.py")
        
    st.markdown("---")
    st.markdown(
        """
        <style>
        .metric-box {
            background-color: #f0f2f6;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 10px;
        }
        </style>
        <div class="metric-box">
            <h4 style="margin:0; color:#2ecc71;">✓ 100% Accurate Math</h4>
            <small>Automated Reconciliation Chain</small>
        </div>
        <div class="metric-box">
            <h4 style="margin:0; color:#3498db;">✓ Verified Tally Formats</h4>
            <small>Double-Checked Summary</small>
        </div>
        """,
        unsafe_allow_html=True 
    )