# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['toml', 'email.mime.text', 'jsonschema', 'MarkupSafe', 'itsdangerous', 'webview', 'bottle', 'app_flask', 'services', 'certifi', 'Deprecated', 'parsers.sbi_parser', 'flask', 'tzdata', 'uvicorn', 'et_xmlfile', 'parsers.cash_parser', 'cffi', 'parsers.bob_parser', 'git', 'smtplib', 'email.mime.multipart', 'pycparser', 'langcodes', 'email.mime.base', 'websockets', 'slicers', 'routes_bank', 'Flask', 'services.logger', 'Jinja2', 'services.xml_generator_hybrid_parser', 'marisa-trie', 'blinker', 'typing_extensions', 'email', 'strategies.FirstChunk', 'pyinstaller-hooks-contrib', 'routes_hybrid', 'referencing', 'routes_download', 'gitdb', 'altgraph', 'wrapt', 'numpy', 'click', 'idna', 'licensing', 'parsers', 'parsers.axis_parser', 'Werkzeug', 'watchdog', 'Flask-Cors', 'services.pdf_reader', 'services.statement_validator', 'tenacity', 'parsers.router', 'regex', 'requests', 'six', 'strategies.WholeChunk', 'email.mime', 'services.xlsx_viewer', 'strategies', 'narwhals', 'rpds-py', 'routes', 'dateutil', 'routes_base', 'email.encoders', 'packaging', 'jaconv', 'pdfplumber', 'multipart', 'slicers.Axis_slicing', 'starlette', 'pyarrow', 'pefile', 'routes_licensing', 'parsers.hybrid_parser', 'aksharamukha', 'lxml', 'httptools', 'werkzeug', 'colorama', 'routes_redact', 'setuptools', 'proxy_tools', 'pdfminer', 'pyinstaller', 'flask_cors', 'jsonschema-specifications', 'pandas', 'openpyxl', 'pypdfium2', 'cryptography', 'slicers.BOB_slicing', 'routes_tally', 'protobuf', 'PyYAML', 'cachetools', 'pillow', 'services.cash_validator', 'slicers.SBI_slicing', 'anyio', 'fitz', 'fonttools', 'routes_gstr1', 'services.cash_xml_generator', 'smmap', 'strategies.ContinuationChunk', 'clr_loader', 'urllib3', 'pythonnet', 'services.cash_xlsx_writer', 'unicodedata2', 'language_data', 'pywin32_ctypes', 'jinja2', 'h11', 'services.xml_generator', 'attrs', 'charset-normalizer', 'pykakasi', 'slicers.hybrid_parser_slicing']
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
