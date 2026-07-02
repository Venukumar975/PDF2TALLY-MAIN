# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['pdfplumber', 'aksharamukha', 'altgraph', 'pycparser', 'pillow', 'dateutil', 'Flask-Cors', 'services.pdf_reader', 'pyarrow', 'jinja2', 'licensing', 'services.statement_validator', 'idna', 'colorama', 'referencing', 'tenacity', 'services.cash_validator', 'attrs', 'strategies', 'langcodes', 'jsonschema', 'pydeck', 'et_xmlfile', 'pypdfium2', 'parsers.router', 'services.xml_generator', 'strategies.FirstChunk', 'parsers.sbi_parser', 'services.logger', 'rpds-py', 'webview', 'werkzeug', 'six', 'lxml', 'pandas', 'language_data', 'cryptography', 'app_flask', 'altair', 'fonttools', 'parsers.cash_parser', 'protobuf', 'cffi', 'pykakasi', 'watchdog', 'itsdangerous', 'httptools', 'flask', 'routes', 'regex', 'git', 'toml', 'plotly', 'parsers', 'services', 'gitdb', 'multipart', 'websockets', 'blinker', 'pyinstaller', 'packaging', 'services.xlsx_viewer', 'Jinja2', 'setuptools', 'openpyxl', 'unicodedata2', 'pywin32-ctypes', 'Flask', 'jaconv', 'click', 'urllib3', 'starlette', 'tzdata', 'Deprecated', 'cachetools', 'pefile', 'strategies.ContinuationChunk', 'typing_extensions', 'clr_loader', 'flask_cors', 'MarkupSafe', 'marisa-trie', 'Werkzeug', 'slicers.BOB_slicing', 'smmap', 'services.cash_xml_generator', 'pdfminer', 'h11', 'charset-normalizer', 'certifi', 'services.cash_xlsx_writer', 'pythonnet', 'wrapt', 'proxy_tools', 'uvicorn', 'bottle', 'numpy', 'pyinstaller-hooks-contrib', 'anyio', 'strategies.WholeChunk', 'parsers.bob_parser', 'PyYAML', 'slicers', 'slicers.SBI_slicing', 'jsonschema-specifications', 'requests', 'narwhals']
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
