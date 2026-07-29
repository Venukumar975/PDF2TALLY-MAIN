# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['dateutil', 'smmap', 'urllib3', 'services.logger', 'slicers', 'werkzeug', 'slicers.Axis_slicing', 'jsonschema', 'Jinja2', 'routes_redact', 'langcodes', 'pycparser', 'bottle', 'setuptools', 'aksharamukha', 'altgraph', 'anyio', 'pyinstaller', 'slicers.hybrid_parser_slicing', 'pillow', 'flask_cors', 'tenacity', 'licensing', 'colorama', 'pdfplumber', 'services.cash_xlsx_writer', 'parsers.sbi_parser', 'services.cash_validator', 'strategies.FirstChunk', 'strategies.WholeChunk', 'git', 'slicers.SBI_slicing', 'parsers.cash_parser', 'starlette', 'language_data', 'protobuf', 'watchdog', 'strategies', 'packaging', 'fitz', 'routes_licensing', 'webview', 'regex', 'parsers.router', 'jaconv', 'parsers.axis_parser', 'pypdfium2', 'marisa-trie', 'services.xml_generator_hybrid_parser', 'numpy', 'routes', 'routes_gstr1', 'tzdata', 'services.xml_generator', 'referencing', 'MarkupSafe', 'typing_extensions', 'idna', 'h11', 'Deprecated', 'uvicorn', 'strategies.ContinuationChunk', 'clr_loader', 'pywin32_ctypes', 'routes_bank', 'pefile', 'et_xmlfile', 'pyarrow', 'services.pdf_reader', 'email.mime.base', 'charset-normalizer', 'app_flask', 'multipart', 'attrs', 'parsers.hybrid_parser', 'parsers.bob_parser', 'slicers.BOB_slicing', 'click', 'proxy_tools', 'services', 'pdfminer', 'email', 'parsers', 'routes_base', 'gitdb', 'openpyxl', 'itsdangerous', 'six', 'jsonschema-specifications', 'services.xlsx_viewer', 'smtplib', 'blinker', 'routes_download', 'email.mime.text', 'wrapt', 'unicodedata2', 'Werkzeug', 'email.mime.multipart', 'email.mime', 'Flask-Cors', 'flask', 'cffi', 'routes_tally', 'cryptography', 'pyinstaller-hooks-contrib', 'cachetools', 'httptools', 'narwhals', 'services.cash_xml_generator', 'pykakasi', 'requests', 'services.statement_validator', 'pandas', 'Flask', 'PyYAML', 'lxml', 'jinja2', 'email.encoders', 'rpds-py', 'routes_hybrid', 'fonttools', 'certifi', 'websockets', 'pythonnet', 'toml']
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
