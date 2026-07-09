# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['parsers.router', 'app_flask', 'parsers.bob_parser', 'tzdata', 'webview', 'et_xmlfile', 'parsers.cash_parser', 'narwhals', 'h11', 'parsers', 'services.pdf_reader', 'click', 'aksharamukha', 'parsers.sbi_parser', 'cryptography', 'lxml', 'language_data', 'slicers.BOB_slicing', 'routes', 'six', 'services.cash_xml_generator', 'services.statement_validator', 'requests', 'attrs', 'typing_extensions', 'MarkupSafe', 'multipart', 'idna', 'pdfminer', 'pythonnet', 'routes_tally', 'Flask-Cors', 'anyio', 'pyinstaller', 'cachetools', 'Jinja2', 'charset-normalizer', 'regex', 'parsers.axis_parser', 'slicers.SBI_slicing', 'services.cash_validator', 'slicers', 'httptools', 'slicers.hybrid_parser_slicing', 'Flask', 'pykakasi', 'Deprecated', 'parsers.hybrid_parser', 'pillow', 'jaconv', 'rpds-py', 'itsdangerous', 'services.xml_generator_hybrid_parser', 'strategies', 'licensing', 'services.xlsx_viewer', 'slicers.Axis_slicing', 'packaging', 'wrapt', 'pycparser', 'marisa-trie', 'git', 'cffi', 'certifi', 'services', 'jsonschema', 'toml', 'langcodes', 'blinker', 'referencing', 'fonttools', 'pandas', 'PyYAML', 'werkzeug', 'flask_cors', 'openpyxl', 'colorama', 'services.logger', 'strategies.FirstChunk', 'bottle', 'pefile', 'tenacity', 'proxy_tools', 'services.cash_xlsx_writer', 'uvicorn', 'strategies.WholeChunk', 'jsonschema-specifications', 'setuptools', 'unicodedata2', 'starlette', 'numpy', 'strategies.ContinuationChunk', 'gitdb', 'watchdog', 'pyinstaller-hooks-contrib', 'services.xml_generator', 'websockets', 'urllib3', 'Werkzeug', 'protobuf', 'pyarrow', 'flask', 'clr_loader', 'pdfplumber', 'pywin32-ctypes', 'smmap', 'dateutil', 'pypdfium2', 'altgraph', 'jinja2']
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
