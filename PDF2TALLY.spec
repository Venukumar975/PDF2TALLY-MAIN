# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['referencing', 'webview', 'email.mime', 'email.encoders', 'email.mime.multipart', 'wrapt', 'idna', 'Jinja2', 'pycparser', 'strategies.ContinuationChunk', 'strategies.WholeChunk', 'unicodedata2', 'email.mime.base', 'MarkupSafe', 'gitdb', 'routes_tally', 'Deprecated', 'jaconv', 'PyYAML', 'anyio', 'slicers.SBI_slicing', 'parsers.hybrid_parser', 'routes_redact', 'flask_cors', 'websockets', 'strategies', 'certifi', 'Werkzeug', 'urllib3', 'pdfplumber', 'dateutil', 'regex', 'slicers', 'parsers', 'multipart', 'pythonnet', 'strategies.FirstChunk', 'cryptography', 'starlette', 'pillow', 'protobuf', 'langcodes', 'httptools', 'toml', 'jinja2', 'requests', 'routes_licensing', 'proxy_tools', 'numpy', 'services.logger', 'services', 'services.pdf_reader', 'services.statement_validator', 'itsdangerous', 'services.cash_xlsx_writer', 'email', 'cachetools', 'werkzeug', 'openpyxl', 'parsers.cash_parser', 'marisa-trie', 'slicers.BOB_slicing', 'jsonschema-specifications', 'pyinstaller', 'routes_hybrid', 'cffi', 'typing_extensions', 'services.xml_generator', 'clr_loader', 'smtplib', 'flask', 'routes_base', 'routes_download', 'pykakasi', 'parsers.axis_parser', 'pdfminer', 'licensing', 'six', 'h11', 'narwhals', 'fonttools', 'bottle', 'et_xmlfile', 'language_data', 'tzdata', 'services.xml_generator_hybrid_parser', 'email.mime.text', 'colorama', 'services.cash_xml_generator', 'click', 'parsers.sbi_parser', 'jsonschema', 'pypdfium2', 'blinker', 'setuptools', 'pyarrow', 'watchdog', 'pywin32-ctypes', 'routes_bank', 'services.xlsx_viewer', 'slicers.hybrid_parser_slicing', 'pyinstaller-hooks-contrib', 'services.cash_validator', 'pefile', 'parsers.router', 'routes_gstr1', 'uvicorn', 'git', 'packaging', 'slicers.Axis_slicing', 'altgraph', 'app_flask', 'parsers.bob_parser', 'aksharamukha', 'charset-normalizer', 'lxml', 'Flask-Cors', 'rpds-py', 'Flask', 'smmap', 'PyMuPDF', 'pandas', 'routes', 'attrs', 'tenacity']
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
