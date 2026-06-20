from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
import zipfile
import xml.etree.ElementTree as ET


NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

ET.register_namespace("", NS_MAIN)
ET.register_namespace("r", NS_REL)


def export_xml_audit_workbook(
    xml_text,
    output_path,
    bank_ledger=None,
    suspense_ledger="Suspense",
):
    root = ET.fromstring(xml_text)
    vouchers = root.findall(".//VOUCHER")

    # Extract opening balance from XML if bank_ledger is specified
    opening_balance = 0.0
    if bank_ledger:
        for ledger_el in root.findall(".//LEDGER"):
            name = (ledger_el.get("NAME") or "").strip()
            if name.upper() == bank_ledger.upper():
                op_bal_el = ledger_el.find("OPENINGBALANCE")
                if op_bal_el is not None and op_bal_el.text:
                    try:
                        # Tally stores debit opening balance as negative string, e.g. -12800.
                        # So opening balance is -float(op_bal_el.text)
                        opening_balance = -float(op_bal_el.text)
                    except ValueError:
                        pass
                break

    voucher_rows = _build_voucher_rows(
        vouchers,
        bank_ledger,
        suspense_ledger,
        opening_balance,
    )

    sheets = [
        (
            "Audit",
            [
                "Date",
                "Voucher Type",
                "Vch No",
                "Debit Ledger (Tally)",
                "Credit Ledger (Tally)",
                "Narration",
                "Debit",
                "Credit",
                "Closing Balance",
            ],
            voucher_rows,
        )
    ]

    _write_xlsx(output_path, sheets)
    return output_path


def _build_voucher_rows(vouchers, bank_ledger, suspense_ledger, opening_balance):
    rows = []
    running_balance = opening_balance

    for voucher in vouchers:
        parsed = _parse_voucher(voucher, bank_ledger, suspense_ledger)

        if parsed["bank_side"] == "Debit":
            running_balance += parsed["bank_amount"]
        elif parsed["bank_side"] == "Credit":
            running_balance -= parsed["bank_amount"]

        rows.append([
            parsed["date"],
            parsed["voucher_type"],
            parsed["voucher_number"],
            parsed["debit_ledger"],
            parsed["credit_ledger"],
            parsed["narration"],
            parsed["debit_amount"],
            parsed["credit_amount"],
            round(running_balance, 2),
        ])

    return rows


def _parse_voucher(voucher, bank_ledger, suspense_ledger):
    voucher_number = voucher.findtext("VOUCHERNUMBER") or ""
    date_value = voucher.findtext("DATE") or ""
    voucher_type = voucher.findtext("VOUCHERTYPENAME") or ""
    narration = voucher.findtext("NARRATION") or ""

    entries = voucher.findall("ALLLEDGERENTRIES.LIST")
    bank_entry = None
    counter_entry = None

    for entry in entries:
        ledger_name = (entry.findtext("LEDGERNAME") or "").strip()
        if bank_ledger and ledger_name.upper() == bank_ledger.upper():
            bank_entry = entry
        elif suspense_ledger and ledger_name.upper() == suspense_ledger.upper():
            counter_entry = entry

    if bank_entry is None and entries:
        bank_entry = entries[0]

    if counter_entry is None and len(entries) > 1:
        counter_entry = entries[1]
    elif counter_entry is None:
        counter_entry = bank_entry

    bank_amount, bank_side, bank_name = _entry_amount_side(bank_entry)
    counter_amount, counter_side, counter_name = _entry_amount_side(counter_entry)

    debit_ledger = ""
    credit_ledger = ""
    debit_amount = ""
    credit_amount = ""

    if bank_side == "Debit":
        debit_ledger = bank_name
        credit_ledger = counter_name
        debit_amount = bank_amount
    else:
        debit_ledger = counter_name
        credit_ledger = bank_name
        credit_amount = bank_amount

    return {
        "voucher_number": voucher_number,
        "date": _from_tally_date(date_value),
        "voucher_type": voucher_type,
        "narration": narration,
        "debit_ledger": debit_ledger,
        "credit_ledger": credit_ledger,
        "debit_amount": debit_amount,
        "credit_amount": credit_amount,
        "bank_side": bank_side,
        "bank_amount": bank_amount if bank_amount else 0.0,
    }


def _entry_amount_side(entry):
    if entry is None:
        return "", "", ""

    ledger_name = entry.findtext("LEDGERNAME") or ""
    amount_text = entry.findtext("AMOUNT") or "0"
    is_deemed_positive = (entry.findtext("ISDEEMEDPOSITIVE") or "").strip().lower() == "yes"
    amount = abs(float(amount_text))
    side = "Debit" if is_deemed_positive else "Credit"

    return amount, side, ledger_name


def _write_xlsx(output_path, sheets):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sheet_names = [_sanitize_sheet_name(name) for name, _, _ in sheets]
    sheet_files = [f"worksheets/sheet{index}.xml" for index in range(1, len(sheets) + 1)]
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml(sheet_files))
        archive.writestr("_rels/.rels", _rels_root_xml())
        archive.writestr("docProps/core.xml", _core_props_xml(now))
        archive.writestr("docProps/app.xml", _app_props_xml(sheet_names))
        archive.writestr("xl/workbook.xml", _workbook_xml(sheet_names))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml(sheet_files))
        archive.writestr("xl/styles.xml", _styles_xml())

        for index, (_, headers, rows) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(headers, rows))


def _worksheet_xml(headers, rows):
    worksheet = ET.Element(f"{{{NS_MAIN}}}worksheet")
    sheet_data = ET.SubElement(worksheet, f"{{{NS_MAIN}}}sheetData")

    _append_row(sheet_data, 1, headers)
    for row_index, row_values in enumerate(rows, start=2):
        _append_row(sheet_data, row_index, row_values)

    return _xml_declaration(ET.tostring(worksheet, encoding="utf-8").decode("utf-8"))


def _append_row(sheet_data, row_number, values):
    row = ET.SubElement(sheet_data, f"{{{NS_MAIN}}}row", {"r": str(row_number)})

    for col_index, value in enumerate(values, start=1):
        if value is None or value == "":
            continue

        cell_ref = f"{_column_name(col_index)}{row_number}"
        cell = ET.SubElement(row, f"{{{NS_MAIN}}}c", {"r": cell_ref})

        if isinstance(value, bool):
            cell.set("t", "inlineStr")
            is_el = ET.SubElement(cell, f"{{{NS_MAIN}}}is")
            t_el = ET.SubElement(is_el, f"{{{NS_MAIN}}}t")
            t_el.text = "TRUE" if value else "FALSE"
            continue

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            v_el = ET.SubElement(cell, f"{{{NS_MAIN}}}v")
            v_el.text = _format_number(value)
            continue

        cell.set("t", "inlineStr")
        is_el = ET.SubElement(cell, f"{{{NS_MAIN}}}is")
        t_el = ET.SubElement(is_el, f"{{{NS_MAIN}}}t")
        t_el.text = str(value)


def _content_types_xml(sheet_files):
    overrides = [
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]

    for sheet_file in sheet_files:
        overrides.append(
            f'<Override PartName="/xl/{sheet_file}" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        *overrides,
        '</Types>',
    ]
    return "".join(parts)


def _rels_root_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        '</Relationships>'
    )


def _workbook_xml(sheet_names):
    sheets_xml = []
    for index, sheet_name in enumerate(sheet_names, start=1):
        sheets_xml.append(
            f'<sheet name="{_xml_attr(sheet_name)}" sheetId="{index}" r:id="rId{index}"/>'
        )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<workbook xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">'
        '<sheets>'
        + "".join(sheets_xml)
        + '</sheets>'
        '</workbook>'
    )


def _workbook_rels_xml(sheet_files):
    relationships = []
    for index, sheet_file in enumerate(sheet_files, start=1):
        relationships.append(
            f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="{sheet_file}"/>'
        )

    relationships.append(
        f'<Relationship Id="rId{len(sheet_files) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{NS_PKG_REL}">'
        + "".join(relationships)
        + '</Relationships>'
    )


def _styles_xml():
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><color theme="1"/><name val="Calibri"/><family val="2"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )


def _core_props_xml(now):
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:creator>Codex</dc:creator>'
        '<cp:lastModifiedBy>Codex</cp:lastModifiedBy>'
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
        '</cp:coreProperties>'
    )


def _app_props_xml(sheet_names):
    sheets = "".join(f"<vt:lpstr>{_xml_text(name)}</vt:lpstr>" for name in sheet_names)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        '<Application>Codex</Application>'
        '<DocSecurity>0</DocSecurity>'
        '<ScaleCrop>false</ScaleCrop>'
        '<HeadingPairs>'
        '<vt:vector size="2" baseType="variant">'
        '<vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant>'
        f'<vt:variant><vt:i4>{len(sheet_names)}</vt:i4></vt:variant>'
        '</vt:vector>'
        '</HeadingPairs>'
        '<TitlesOfParts>'
        f'<vt:vector size="{len(sheet_names)}" baseType="lpstr">{sheets}</vt:vector>'
        '</TitlesOfParts>'
        '</Properties>'
    )


def _xml_declaration(body):
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + body


def _xml_text(value):
    return escape(str(value), {'"': "&quot;"})


def _xml_attr(value):
    return _xml_text(value)


def _sanitize_sheet_name(name):
    cleaned = "".join(ch if ch not in '[]:*?/\\' else " " for ch in name).strip()
    return cleaned[:31] or "Sheet"


def _column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _format_number(value):
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{float(value):.2f}".rstrip("0").rstrip(".")


def _from_tally_date(date_value):
    if not date_value:
        return ""

    return datetime.strptime(date_value, "%Y%m%d").strftime("%d-%m-%Y")
