# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['gitdb', 'altgraph', 'toml', 'unicodedata2', 'fitz', 'language_data', 'email.mime.multipart', 'licensing', 'routes', 'parsers.cash_parser', 'email', 'PyYAML', 'email.mime.text', 'email.mime.base', 'parsers.hybrid_parser', 'attrs', 'Jinja2', 'fonttools', 'click', 'slicers.BOB_slicing', 'jsonschema', 'clr_loader', 'strategies.ContinuationChunk', 'services.logger', 'slicers.hybrid_parser_slicing', 'lxml', 'jaconv', 'pykakasi', 'pywin32_ctypes', 'app_flask', 'tzdata', 'aksharamukha', 'strategies.WholeChunk', 'email.mime', 'parsers.bob_parser', 'slicers.Axis_slicing', 'routes_base', 'regex', 'services', 'routes_licensing', 'et_xmlfile', 'narwhals', 'routes_download', 'pyarrow', 'routes_tally', 'tenacity', 'httptools', 'routes_hybrid', 'routes_bank', 'starlette', 'referencing', 'uvicorn', 'pdfplumber', 'slicers.SBI_slicing', 'cryptography', 'jinja2', 'pefile', 'cffi', 'services.pdf_reader', 'urllib3', 'routes_gstr1', 'packaging', 'services.cash_xlsx_writer', 'typing_extensions', 'services.statement_validator', 'services.xml_generator', 'services.cash_xml_generator', 'pdfminer', 'proxy_tools', 'slicers', 'marisa-trie', 'certifi', 'h11', 'parsers', 'strategies', 'Deprecated', 'idna', 'pyinstaller', 'blinker', 'setuptools', 'dateutil', 'Werkzeug', 'strategies.FirstChunk', 'cachetools', 'parsers.sbi_parser', 'email.encoders', 'pillow', 'charset-normalizer', 'smtplib', 'itsdangerous', 'pyinstaller-hooks-contrib', 'openpyxl', 'protobuf', 'requests', 'MarkupSafe', 'flask', 'smmap', 'watchdog', 'Flask', 'wrapt', 'pycparser', 'flask_cors', 'parsers.axis_parser', 'langcodes', 'colorama', 'rpds-py', 'services.cash_validator', 'routes_redact', 'multipart', 'webview', 'anyio', 'websockets', 'services.xlsx_viewer', 'jsonschema-specifications', 'six', 'pythonnet', 'services.xml_generator_hybrid_parser', 'numpy', 'pypdfium2', 'Flask-Cors', 'bottle', 'git', 'werkzeug', 'pandas', 'parsers.router']
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
