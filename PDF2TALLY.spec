# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['slicers', 'parsers', 'cffi', 'Flask-Cors', 'click', 'tenacity', 'jsonschema-specifications', 'services.cash_validator', 'clr_loader', 'parsers.bob_parser', 'Deprecated', 'dateutil', 'unicodedata2', 'blinker', 'fitz', 'pycparser', 'typing_extensions', 'routes', 'gitdb', 'pykakasi', 'itsdangerous', 'git', 'parsers.axis_parser', 'openpyxl', 'routes_bank', 'cachetools', 'uvicorn', 'pyinstaller-hooks-contrib', 'fonttools', 'httptools', 'pefile', 'Jinja2', 'bottle', 'slicers.Axis_slicing', 'multipart', 'services.logger', 'jinja2', 'parsers.hybrid_parser', 'routes_licensing', 'services.xlsx_viewer', 'strategies.WholeChunk', 'charset-normalizer', 'colorama', 'tzdata', 'routes_base', 'slicers.hybrid_parser_slicing', 'licensing', 'slicers.SBI_slicing', 'PyYAML', 'services', 'jaconv', 'urllib3', 'pywin32_ctypes', 'pythonnet', 'flask_cors', 'smtplib', 'protobuf', 'routes_redact', 'parsers.cash_parser', 'requests', 'werkzeug', 'email.mime', 'six', 'watchdog', 'pyinstaller', 'email.mime.base', 'lxml', 'pdfminer', 'services.xml_generator_hybrid_parser', 'pdfplumber', 'aksharamukha', 'pillow', 'starlette', 'marisa-trie', 'MarkupSafe', 'idna', 'language_data', 'pandas', 'smmap', 'services.cash_xlsx_writer', 'Flask', 'routes_download', 'et_xmlfile', 'rpds-py', 'setuptools', 'numpy', 'webview', 'pyarrow', 'regex', 'jsonschema', 'app_flask', 'wrapt', 'strategies', 'services.xml_generator', 'referencing', 'slicers.BOB_slicing', 'email', 'langcodes', 'routes_gstr1', 'services.cash_xml_generator', 'strategies.FirstChunk', 'attrs', 'email.mime.text', 'routes_tally', 'narwhals', 'Werkzeug', 'parsers.router', 'cryptography', 'certifi', 'packaging', 'toml', 'services.pdf_reader', 'flask', 'email.encoders', 'pypdfium2', 'altgraph', 'anyio', 'email.mime.multipart', 'routes_hybrid', 'services.statement_validator', 'parsers.sbi_parser', 'strategies.ContinuationChunk', 'proxy_tools', 'websockets', 'h11']
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
