# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['flask_cors', 'proxy_tools', 'setuptools', 'Flask', 'email.mime.text', 'routes_redact', 'narwhals', 'app_flask', 'email.encoders', 'referencing', 'rpds-py', 'requests', 'email.mime.base', 'regex', 'altgraph', 'fonttools', 'routes_tally', 'parsers.bob_parser', 'jsonschema', 'attrs', 'slicers.Axis_slicing', 'et_xmlfile', 'tenacity', 'routes_gstr1', 'strategies.WholeChunk', 'bottle', 'services.statement_validator', 'slicers.BOB_slicing', 'email.mime', 'licensing', 'routes_hybrid', 'cachetools', 'pandas', 'services.xml_generator_hybrid_parser', 'h11', 'clr_loader', 'aksharamukha', 'jsonschema-specifications', 'charset-normalizer', 'services.logger', 'parsers.cash_parser', 'pyinstaller-hooks-contrib', 'services.cash_xlsx_writer', 'typing_extensions', 'services.pdf_reader', 'parsers.axis_parser', 'slicers', 'pythonnet', 'parsers.hybrid_parser', 'Deprecated', 'marisa-trie', 'routes', 'parsers.router', 'Werkzeug', 'pycparser', 'language_data', 'blinker', 'cryptography', 'jinja2', 'six', 'wrapt', 'pillow', 'protobuf', 'starlette', 'certifi', 'routes_licensing', 'toml', 'smtplib', 'email.mime.multipart', 'packaging', 'websockets', 'webview', 'jaconv', 'MarkupSafe', 'routes_download', 'idna', 'PyYAML', 'pyinstaller', 'strategies.ContinuationChunk', 'colorama', 'watchdog', 'pefile', 'tzdata', 'Flask-Cors', 'pywin32-ctypes', 'routes_base', 'services.cash_validator', 'pyarrow', 'strategies.FirstChunk', 'cffi', 'pykakasi', 'PyMuPDF', 'Jinja2', 'anyio', 'dateutil', 'strategies', 'slicers.SBI_slicing', 'werkzeug', 'git', 'lxml', 'services.cash_xml_generator', 'email', 'services.xml_generator', 'click', 'services.xlsx_viewer', 'uvicorn', 'numpy', 'pdfminer', 'langcodes', 'multipart', 'services', 'pdfplumber', 'parsers.sbi_parser', 'gitdb', 'openpyxl', 'httptools', 'parsers', 'pypdfium2', 'smmap', 'routes_bank', 'slicers.hybrid_parser_slicing', 'urllib3', 'unicodedata2', 'flask', 'itsdangerous']
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
    name='PDF2TALLY',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDF2TALLY',
)
