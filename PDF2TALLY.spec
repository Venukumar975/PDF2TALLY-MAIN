# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['Jinja2', 'certifi', 'marisa-trie', 'routes_gstr1', 'services.logger', 'tzdata', 'routes_download', 'pyinstaller', 'uvicorn', 'cachetools', 'idna', 'tenacity', 'email.mime.base', 'colorama', 'fitz', 'multipart', 'lxml', 'openpyxl', 'routes_redact', 'parsers.hybrid_parser', 'strategies', 'slicers', 'services', 'Flask', 'routes_licensing', 'packaging', 'unicodedata2', 'narwhals', 'routes_base', 'strategies.FirstChunk', 'Werkzeug', 'wrapt', 'routes_tally', 'email.mime', 'slicers.BOB_slicing', 'websockets', 'smmap', 'dateutil', 'strategies.WholeChunk', 'pywin32_ctypes', 'pillow', 'flask', 'routes_hybrid', 'licensing', 'pdfminer', 'email.mime.multipart', 'strategies.ContinuationChunk', 'watchdog', 'cffi', 'urllib3', 'services.xlsx_viewer', 'smtplib', 'pykakasi', 'parsers.axis_parser', 'attrs', 'pycparser', 'click', 'parsers.cash_parser', 'parsers.sbi_parser', 'pandas', 'routes_bank', 'slicers.hybrid_parser_slicing', 'jsonschema-specifications', 'requests', 'Deprecated', 'starlette', 'email.mime.text', 'parsers.router', 'et_xmlfile', 'pyinstaller-hooks-contrib', 'langcodes', 'pyarrow', 'email.encoders', 'slicers.SBI_slicing', 'setuptools', 'protobuf', 'routes', 'werkzeug', 'anyio', 'services.cash_xml_generator', 'jaconv', 'bottle', 'jsonschema', 'altgraph', 'regex', 'itsdangerous', 'typing_extensions', 'slicers.Axis_slicing', 'h11', 'rpds-py', 'services.pdf_reader', 'services.xml_generator', 'parsers', 'pdfplumber', 'jinja2', 'git', 'MarkupSafe', 'flask_cors', 'webview', 'numpy', 'referencing', 'services.cash_validator', 'app_flask', 'services.xml_generator_hybrid_parser', 'language_data', 'six', 'Flask-Cors', 'pythonnet', 'parsers.bob_parser', 'cryptography', 'services.statement_validator', 'toml', 'charset-normalizer', 'gitdb', 'httptools', 'proxy_tools', 'pypdfium2', 'clr_loader', 'pefile', 'fonttools', 'PyYAML', 'services.cash_xlsx_writer', 'aksharamukha', 'blinker', 'email']
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
