# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['cryptography', 'requests', 'pefile', 'werkzeug', 'httptools', 'unicodedata2', 'protobuf', 'regex', 'services.xml_generator', 'smmap', 'MarkupSafe', 'attrs', 'typing_extensions', 'pythonnet', 'strategies.WholeChunk', 'cffi', 'gitdb', 'altgraph', 'parsers.sbi_parser', 'email.mime.base', 'email.encoders', 'webview', 'routes_gstr1', 'services.pdf_reader', 'pyinstaller-hooks-contrib', 'Deprecated', 'slicers.Axis_slicing', 'routes_base', 'tzdata', 'Werkzeug', 'toml', 'parsers.axis_parser', 'numpy', 'fonttools', 'bottle', 'fitz', 'services.cash_validator', 'services.statement_validator', 'lxml', 'uvicorn', 'slicers.SBI_slicing', 'parsers.cash_parser', 'itsdangerous', 'pdfplumber', 'parsers.bob_parser', 'email', 'starlette', 'services.xlsx_viewer', 'services.cash_xml_generator', 'flask', 'et_xmlfile', 'parsers.hybrid_parser', 'routes', 'packaging', 'proxy_tools', 'pypdfium2', 'jsonschema-specifications', 'slicers.hybrid_parser_slicing', 'narwhals', 'h11', 'routes_bank', 'smtplib', 'services', 'Flask', 'slicers', 'slicers.BOB_slicing', 'parsers', 'marisa-trie', 'aksharamukha', 'services.cash_xlsx_writer', 'pywin32_ctypes', 'jinja2', 'clr_loader', 'pyarrow', 'PyYAML', 'licensing', 'strategies', 'langcodes', 'pandas', 'dateutil', 'flask_cors', 'click', 'referencing', 'email.mime.multipart', 'email.mime.text', 'charset-normalizer', 'pdfminer', 'certifi', 'pykakasi', 'watchdog', 'urllib3', 'services.xml_generator_hybrid_parser', 'git', 'pyinstaller', 'jaconv', 'routes_licensing', 'tenacity', 'language_data', 'routes_redact', 'wrapt', 'setuptools', 'app_flask', 'jsonschema', 'parsers.router', 'pycparser', 'cachetools', 'email.mime', 'rpds-py', 'routes_download', 'openpyxl', 'routes_hybrid', 'multipart', 'Flask-Cors', 'websockets', 'colorama', 'blinker', 'six', 'services.logger', 'routes_tally', 'strategies.FirstChunk', 'anyio', 'pillow', 'strategies.ContinuationChunk', 'idna', 'Jinja2']
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
    a.binaries,
    a.datas,
    [],
    name='PDF2TALLY',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['logo.ico'],
)
