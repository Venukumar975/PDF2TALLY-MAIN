# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['services.xml_generator', 'smmap', 'services', 'Deprecated', 'altgraph', 'routes', 'langcodes', 'strategies.WholeChunk', 'wrapt', 'strategies', 'regex', 'MarkupSafe', 'protobuf', 'starlette', 'attrs', 'routes_bank', 'werkzeug', 'clr_loader', 'services.xml_generator_hybrid_parser', 'slicers.BOB_slicing', 'routes_base', 'fonttools', 'gitdb', 'h11', 'tenacity', 'Flask-Cors', 'app_flask', 'marisa-trie', 'Jinja2', 'parsers', 'slicers.hybrid_parser_slicing', 'cffi', 'pyinstaller-hooks-contrib', 'requests', 'routes_tally', 'pillow', 'aksharamukha', 'certifi', 'Werkzeug', 'services.cash_validator', 'dateutil', 'cryptography', 'colorama', 'services.statement_validator', 'pefile', 'numpy', 'Flask', 'parsers.sbi_parser', 'et_xmlfile', 'websockets', 'pywin32-ctypes', 'click', 'routes_hybrid', 'pythonnet', 'tzdata', 'toml', 'lxml', 'cachetools', 'multipart', 'licensing', 'services.xlsx_viewer', 'uvicorn', 'six', 'pdfminer', 'routes_download', 'bottle', 'pdfplumber', 'openpyxl', 'webview', 'charset-normalizer', 'strategies.ContinuationChunk', 'itsdangerous', 'flask', 'pyinstaller', 'parsers.router', 'routes_licensing', 'proxy_tools', 'pyarrow', 'parsers.hybrid_parser', 'rpds-py', 'typing_extensions', 'blinker', 'httptools', 'referencing', 'flask_cors', 'git', 'jinja2', 'packaging', 'jaconv', 'pykakasi', 'urllib3', 'jsonschema-specifications', 'services.logger', 'services.cash_xlsx_writer', 'slicers.Axis_slicing', 'parsers.bob_parser', 'narwhals', 'unicodedata2', 'routes_gstr1', 'parsers.cash_parser', 'jsonschema', 'PyYAML', 'anyio', 'watchdog', 'setuptools', 'parsers.axis_parser', 'pycparser', 'slicers.SBI_slicing', 'pandas', 'slicers', 'services.cash_xml_generator', 'idna', 'pypdfium2', 'services.pdf_reader', 'language_data', 'strategies.FirstChunk']
tmp_ret = collect_all('pdfplumber')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pypdfium2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('flask')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('aksharamukha')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['obf_dist\\desktop_run.py'],
    pathex=['obf_dist'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pdf2tallyXML',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pdf2tallyXML',
)
