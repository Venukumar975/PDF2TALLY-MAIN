# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['routes_download', 'pypdfium2', 'jsonschema-specifications', 'idna', 'flask', 'colorama', 'routes', 'services.xlsx_viewer', 'six', 'services.statement_validator', 'watchdog', 'pillow', 'parsers.bob_parser', 'email.mime', 'strategies.ContinuationChunk', 'fitz', 'bottle', 'uvicorn', 'certifi', 'routes_hybrid', 'email', 'urllib3', 'routes_bank', 'pdfplumber', 'services.cash_xlsx_writer', 'smtplib', 'regex', 'Deprecated', 'charset-normalizer', 'requests', 'parsers.hybrid_parser', 'slicers.BOB_slicing', 'services.pdf_reader', 'httptools', 'routes_base', 'Werkzeug', 'routes_licensing', 'jaconv', 'pyarrow', 'multipart', 'services', 'slicers.SBI_slicing', 'tzdata', 'wrapt', 'parsers', 'routes_redact', 'fonttools', 'PyYAML', 'setuptools', 'typing_extensions', 'packaging', 'pykakasi', 'strategies.WholeChunk', 'h11', 'Flask-Cors', 'pandas', 'langcodes', 'services.cash_xml_generator', 'strategies', 'pyinstaller', 'click', 'MarkupSafe', 'starlette', 'pythonnet', 'pdfminer', 'jinja2', 'narwhals', 'openpyxl', 'email.mime.base', 'webview', 'clr_loader', 'licensing', 'parsers.cash_parser', 'slicers.hybrid_parser_slicing', 'proxy_tools', 'itsdangerous', 'routes_tally', 'numpy', 'Jinja2', 'parsers.axis_parser', 'pyinstaller-hooks-contrib', 'app_flask', 'gitdb', 'pycparser', 'werkzeug', 'cffi', 'Flask', 'slicers', 'websockets', 'services.xml_generator_hybrid_parser', 'attrs', 'jsonschema', 'marisa-trie', 'services.cash_validator', 'dateutil', 'services.xml_generator', 'email.mime.multipart', 'et_xmlfile', 'strategies.FirstChunk', 'cachetools', 'smmap', 'tenacity', 'slicers.Axis_slicing', 'blinker', 'pywin32_ctypes', 'routes_gstr1', 'services.logger', 'anyio', 'email.mime.text', 'flask_cors', 'unicodedata2', 'aksharamukha', 'pefile', 'referencing', 'parsers.sbi_parser', 'rpds-py', 'parsers.router', 'cryptography', 'git', 'altgraph', 'lxml', 'toml', 'protobuf', 'email.encoders', 'language_data']
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
