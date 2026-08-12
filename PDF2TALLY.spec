# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['services.cash_xlsx_writer', 'requests', 'pdfplumber', 'email.encoders', 'jinja2', 'strategies', 'setuptools', 'smtplib', 'fitz', 'langcodes', 'pyinstaller', 'Deprecated', 'uvicorn', 'urllib3', 'services.cash_validator', 'certifi', 'language_data', 'services.statement_validator', 'services', 'services.cash_xml_generator', 'slicers.hybrid_parser_slicing', 'aksharamukha', 'cachetools', 'flask_cors', 'unicodedata2', 'routes_bank', 'email', 'git', 'Flask', 'routes', 'wrapt', 'services.xlsx_viewer', 'strategies.FirstChunk', 'email.mime.base', 'tenacity', 'pyarrow', 'routes_base', 'webview', 'protobuf', 'et_xmlfile', 'strategies.ContinuationChunk', 'routes_gstr1', 'starlette', 'regex', 'routes_download', 'jsonschema-specifications', 'referencing', 'pypdfium2', 'Werkzeug', 'parsers.router', 'blinker', 'MarkupSafe', 'pycparser', 'app_flask', 'tzdata', 'routes_tally', 'toml', 'slicers.SBI_slicing', 'pillow', 'parsers.axis_parser', 'proxy_tools', 'pykakasi', 'cffi', 'anyio', 'colorama', 'slicers.Axis_slicing', 'werkzeug', 'itsdangerous', 'routes_redact', 'watchdog', 'email.mime.multipart', 'Jinja2', 'charset-normalizer', 'rpds-py', 'gitdb', 'marisa-trie', 'pythonnet', 'narwhals', 'bottle', 'httptools', 'altgraph', 'slicers.BOB_slicing', 'packaging', 'websockets', 'click', 'jaconv', 'idna', 'email.mime.text', 'services.logger', 'pdfminer', 'h11', 'licensing', 'services.pdf_reader', 'Flask-Cors', 'cryptography', 'parsers.bob_parser', 'parsers.cash_parser', 'PyYAML', 'flask', 'strategies.WholeChunk', 'clr_loader', 'pefile', 'email.mime', 'routes_licensing', 'parsers', 'fonttools', 'multipart', 'parsers.sbi_parser', 'smmap', 'parsers.hybrid_parser', 'routes_hybrid', 'pandas', 'jsonschema', 'openpyxl', 'lxml', 'attrs', 'slicers', 'dateutil', 'six', 'services.xml_generator_hybrid_parser', 'typing_extensions', 'services.xml_generator', 'numpy', 'pyinstaller-hooks-contrib', 'pywin32_ctypes']
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
