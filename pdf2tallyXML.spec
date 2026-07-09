# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['PyYAML', 'app_flask', 'bottle', 'httptools', 'jsonschema-specifications', 'services.logger', 'urllib3', 'parsers.hybrid_parser', 'tzdata', 'gitdb', 'websockets', 'numpy', 'toml', 'slicers', 'marisa-trie', 'referencing', 'openpyxl', 'wrapt', 'parsers.sbi_parser', 'git', 'slicers.hybrid_parser_slicing', 'jaconv', 'Flask-Cors', 'pyinstaller', 'proxy_tools', 'pycparser', 'pillow', 'jsonschema', 'services.statement_validator', 'pandas', 'tenacity', 'charset-normalizer', 'anyio', 'strategies.FirstChunk', 'cryptography', 'services.cash_xlsx_writer', 'pythonnet', 'pyarrow', 'services.xlsx_viewer', 'parsers.cash_parser', 'rpds-py', 'slicers.BOB_slicing', 'routes', 'multipart', 'services.cash_validator', 'services.xml_generator', 'parsers.bob_parser', 'packaging', 'starlette', 'pdfplumber', 'colorama', 'h11', 'services', 'services.pdf_reader', 'cffi', 'services.cash_xml_generator', 'parsers', 'blinker', 'itsdangerous', 'protobuf', 'pypdfium2', 'pyinstaller-hooks-contrib', 'pefile', 'fonttools', 'pywin32-ctypes', 'requests', 'idna', 'services.xml_generator_hybrid_parser', 'language_data', 'webview', 'regex', 'six', 'strategies', 'pdfminer', 'narwhals', 'uvicorn', 'routes_tally', 'lxml', 'parsers.axis_parser', 'unicodedata2', 'strategies.ContinuationChunk', 'setuptools', 'smmap', 'langcodes', 'werkzeug', 'altgraph', 'clr_loader', 'cachetools', 'MarkupSafe', 'parsers.router', 'dateutil', 'strategies.WholeChunk', 'slicers.Axis_slicing', 'et_xmlfile', 'pykakasi', 'certifi', 'flask', 'jinja2', 'aksharamukha', 'Jinja2', 'licensing', 'Werkzeug', 'flask_cors', 'typing_extensions', 'Flask', 'watchdog', 'slicers.SBI_slicing', 'attrs', 'click', 'Deprecated']
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
    [],
    exclude_binaries=True,
    name='pdf2tallyXML',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pdf2tallyXML',
)
