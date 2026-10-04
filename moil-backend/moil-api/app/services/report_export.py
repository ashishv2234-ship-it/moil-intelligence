"""CSV and Excel (.xlsx) writers using only the standard library (no pandas/openpyxl needed)."""
import csv, io, zipfile
from xml.sax.saxutils import escape

def to_csv(ds: dict) -> bytes:
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(ds["columns"]); w.writerows(ds["rows"])
    return buf.getvalue().encode("utf-8-sig")  # BOM so Excel reads UTF-8 correctly

def _col(i: int) -> str:
    s = ""
    i += 1
    while i: i, r = divmod(i - 1, 26); s = chr(65 + r) + s
    return s

def _cell(ref: str, v, style: int = 0) -> str:
    if v is None or v == "": return ""
    if isinstance(v, bool): v = str(v)
    if isinstance(v, (int, float)): return f'<c r="{ref}" s="{style}"><v>{v}</v></c>'
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(str(v))}</t></is></c>'

def to_xlsx(ds: dict) -> bytes:
    rows_xml, r = [], 1
    def add(values, style=0):
        nonlocal r
        cells = "".join(_cell(f"{_col(i)}{r}", v, style) for i, v in enumerate(values))
        rows_xml.append(f'<row r="{r}">{cells}</row>'); r += 1
    add([ds["title"]], 1)
    add([ds.get("note") or ""])
    add([f'Generated {ds.get("generated_at", "")}'])
    r += 1  # blank row
    add(ds["columns"], 1)
    for row in ds["rows"]: add(row)
    widths = [max([len(str(ds["columns"][i]))] + [len(str(x[i])) for x in ds["rows"][:200]]) + 3 for i in range(len(ds["columns"]))]
    cols = "".join(f'<col min="{i+1}" max="{i+1}" width="{min(w, 60)}" customWidth="1"/>' for i, w in enumerate(widths))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    sheet = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet {ns}><cols>{cols}</cols><sheetData>{"".join(rows_xml)}</sheetData></worksheet>'
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet {ns}><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
              '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
              '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    wb = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook {ns} xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<sheets><sheet name="Report" sheetId="1" r:id="rId1"/></sheets></workbook>')
    wbrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
              '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
              '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels); z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/_rels/workbook.xml.rels", wbrels); z.writestr("xl/worksheets/sheet1.xml", sheet); z.writestr("xl/styles.xml", styles)
    return out.getvalue()
