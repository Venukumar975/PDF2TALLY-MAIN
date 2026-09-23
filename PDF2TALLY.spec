# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['requests', 'werkzeug', 'et_xmlfile', 'routes', 'click', 'email', 'parsers.cash_parser', 'openpyxl', 'pywin32_ctypes', 'wrapt', 'aksharamukha', 'Flask', 'routes_bank', 'jsonschema-specifications', 'langcodes', 'flask_cors', 'parsers.axis_parser', 'routes_download', 'pythonnet', 'parsers.router', 'regex', 'tenacity', 'blinker', 'app_flask', 'fonttools', 'pyinstaller-hooks-contrib', 'toml', 'strategies.ContinuationChunk', 'unicodedata2', 'routes_redact', 'MarkupSafe', 'services.cash_xml_generator', 'pycparser', 'language_data', 'slicers.hybrid_parser_slicing', 'services.cash_xlsx_writer', 'flask', 'setuptools', 'packaging', 'cryptography', 'strategies.WholeChunk', 'services.xml_generator', 'email.mime.text', 'email.mime.multipart', 'fitz', 'routes_tally', 'services.statement_validator', 'services.xlsx_viewer', 'referencing', 'websockets', 'certifi', 'colorama', 'narwhals', 'smtplib', 'routes_base', 'email.encoders', 'git', 'slicers.Axis_slicing', 'rpds-py', 'Jinja2', 'urllib3', 'uvicorn', 'pefile', 'Deprecated', 'Flask-Cors', 'parsers.bob_parser', 'h11', 'services', 'gitdb', 'pandas', 'lxml', 'services.cash_validator', 'anyio', 'marisa-trie', 'routes_gstr1', 'charset-normalizer', 'services.logger', 'pdfminer', 'typing_extensions', 'six', 'starlette', 'cachetools', 'idna', 'services.xml_generator_hybrid_parser', 'itsdangerous', 'strategies.FirstChunk', 'parsers.sbi_parser', 'parsers.hybrid_parser', 'jaconv', 'slicers', 'dateutil', 'protobuf', 'watchdog', 'tzdata', 'parsers', 'jsonschema', 'pyinstaller', 'numpy', 'pypdfium2', 'attrs', 'routes_licensing', 'PyYAML', 'pyarrow', 'smmap', 'altgraph', 'bottle', 'pillow', 'licensing', 'slicers.SBI_slicing', 'proxy_tools', 'services.pdf_reader', 'pykakasi', 'webview', 'clr_loader', 'routes_hybrid', 'email.mime.base', 'multipart', 'Werkzeug', 'jinja2', 'cffi', 'email.mime', 'strategies', 'slicers.BOB_slicing', 'httptools', 'pdfplumber']
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
