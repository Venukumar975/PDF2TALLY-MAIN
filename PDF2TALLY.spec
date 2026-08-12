# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['fitz', 'et_xmlfile', 'Werkzeug', 'parsers.cash_parser', 'parsers.bob_parser', 'narwhals', 'smtplib', 'wrapt', 'services.xml_generator_hybrid_parser', 'itsdangerous', 'packaging', 'slicers', 'flask_cors', 'pillow', 'lxml', 'licensing', 'flask', 'bottle', 'setuptools', 'strategies.FirstChunk', 'proxy_tools', 'pandas', 'tenacity', 'email.mime', 'certifi', 'strategies.ContinuationChunk', 'h11', 'routes_licensing', 'pyinstaller-hooks-contrib', 'services.pdf_reader', 'pdfplumber', 'numpy', 'jinja2', 'unicodedata2', 'gitdb', 'Flask', 'routes_base', 'multipart', 'pdfminer', 'services.cash_xlsx_writer', 'requests', 'slicers.hybrid_parser_slicing', 'services.cash_xml_generator', 'langcodes', 'services.statement_validator', 'MarkupSafe', 'parsers.axis_parser', 'rpds-py', 'email.mime.base', 'routes_gstr1', 'email.mime.text', 'idna', 'fonttools', 'altgraph', 'pythonnet', 'blinker', 'click', 'services.xml_generator', 'werkzeug', 'routes_bank', 'Deprecated', 'cffi', 'toml', 'parsers', 'slicers.Axis_slicing', 'dateutil', 'typing_extensions', 'pyarrow', 'jaconv', 'pycparser', 'strategies.WholeChunk', 'aksharamukha', 'pyinstaller', 'urllib3', 'charset-normalizer', 'webview', 'regex', 'slicers.BOB_slicing', 'pywin32_ctypes', 'services.cash_validator', 'parsers.router', 'tzdata', 'colorama', 'websockets', 'marisa-trie', 'jsonschema-specifications', 'slicers.SBI_slicing', 'six', 'services.logger', 'anyio', 'protobuf', 'email.mime.multipart', 'pykakasi', 'PyYAML', 'routes_redact', 'pefile', 'parsers.hybrid_parser', 'parsers.sbi_parser', 'Flask-Cors', 'httptools', 'routes_hybrid', 'starlette', 'cachetools', 'uvicorn', 'app_flask', 'referencing', 'routes', 'openpyxl', 'routes_download', 'jsonschema', 'watchdog', 'routes_tally', 'cryptography', 'git', 'services.xlsx_viewer', 'strategies', 'pypdfium2', 'clr_loader', 'smmap', 'language_data', 'email', 'services', 'email.encoders', 'Jinja2', 'attrs']
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
