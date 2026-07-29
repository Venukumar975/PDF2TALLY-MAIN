# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['watchdog', 'Werkzeug', 'pycparser', 'strategies.FirstChunk', 'routes_redact', 'cffi', 'numpy', 'aksharamukha', 'strategies', 'openpyxl', 'blinker', 'slicers.Axis_slicing', 'pandas', 'proxy_tools', 'attrs', 'strategies.WholeChunk', 'smmap', 'pdfplumber', 'narwhals', 'pywin32_ctypes', 'parsers.sbi_parser', 'services.statement_validator', 'bottle', 'routes_base', 'werkzeug', 'parsers', 'slicers', 'clr_loader', 'typing_extensions', 'routes_gstr1', 'PyYAML', 'six', 'Jinja2', 'rpds-py', 'gitdb', 'packaging', 'regex', 'flask', 'routes_licensing', 'routes_bank', 'services.cash_xml_generator', 'Flask', 'licensing', 'Deprecated', 'services.xml_generator', 'charset-normalizer', 'requests', 'routes', 'email.encoders', 'services', 'websockets', 'certifi', 'setuptools', 'fitz', 'cryptography', 'jsonschema-specifications', 'multipart', 'routes_download', 'strategies.ContinuationChunk', 'services.cash_validator', 'dateutil', 'tenacity', 'colorama', 'pillow', 'parsers.bob_parser', 'services.cash_xlsx_writer', 'pyinstaller', 'pypdfium2', 'pythonnet', 'urllib3', 'click', 'parsers.cash_parser', 'h11', 'services.pdf_reader', 'tzdata', 'parsers.axis_parser', 'referencing', 'itsdangerous', 'jaconv', 'email.mime.base', 'cachetools', 'Flask-Cors', 'parsers.hybrid_parser', 'language_data', 'fonttools', 'anyio', 'altgraph', 'httptools', 'wrapt', 'routes_hybrid', 'unicodedata2', 'idna', 'et_xmlfile', 'email.mime.text', 'slicers.hybrid_parser_slicing', 'flask_cors', 'git', 'langcodes', 'app_flask', 'email.mime.multipart', 'protobuf', 'pyarrow', 'MarkupSafe', 'toml', 'pykakasi', 'services.xml_generator_hybrid_parser', 'pdfminer', 'email', 'marisa-trie', 'uvicorn', 'slicers.SBI_slicing', 'slicers.BOB_slicing', 'lxml', 'jinja2', 'services.logger', 'smtplib', 'email.mime', 'services.xlsx_viewer', 'pefile', 'starlette', 'jsonschema', 'pyinstaller-hooks-contrib', 'webview', 'parsers.router', 'routes_tally']
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
