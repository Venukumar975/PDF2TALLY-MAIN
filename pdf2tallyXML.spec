# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['git', 'websockets', 'MarkupSafe', 'slicers.SBI_slicing', 'attrs', 'services.statement_validator', 'typing_extensions', 'jsonschema', 'packaging', 'services.logger', 'services.xml_generator', 'pyarrow', 'flask_cors', 'clr_loader', 'gitdb', 'cffi', 'pycparser', 'services', 'regex', 'pykakasi', 'jinja2', 'parsers.sbi_parser', 'werkzeug', 'aksharamukha', 'pyinstaller', 'pdfminer', 'httptools', 'language_data', 'pythonnet', 'colorama', 'lxml', 'parsers.cash_parser', 'itsdangerous', 'jaconv', 'Flask', 'protobuf', 'Deprecated', 'app_flask', 'altgraph', 'setuptools', 'slicers.BOB_slicing', 'tenacity', 'Flask-Cors', 'services.cash_validator', 'dateutil', 'strategies.FirstChunk', 'strategies.WholeChunk', 'pypdfium2', 'pdfplumber', 'parsers.bob_parser', 'urllib3', 'Jinja2', 'watchdog', 'services.cash_xlsx_writer', 'pandas', 'Werkzeug', 'fonttools', 'tzdata', 'marisa-trie', 'click', 'routes', 'proxy_tools', 'rpds-py', 'starlette', 'referencing', 'parsers.router', 'PyYAML', 'charset-normalizer', 'smmap', 'h11', 'numpy', 'pefile', 'services.pdf_reader', 'strategies.ContinuationChunk', 'webview', 'services.cash_xml_generator', 'narwhals', 'certifi', 'requests', 'toml', 'bottle', 'wrapt', 'services.xlsx_viewer', 'blinker', 'et_xmlfile', 'multipart', 'pywin32-ctypes', 'strategies', 'slicers', 'idna', 'six', 'unicodedata2', 'flask', 'pyinstaller-hooks-contrib', 'openpyxl', 'cachetools', 'jsonschema-specifications', 'anyio', 'pillow', 'parsers', 'uvicorn', 'langcodes', 'cryptography', 'licensing']
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
