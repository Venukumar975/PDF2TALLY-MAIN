# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['services.logger', 'unicodedata2', 'setuptools', 'parsers', 'aksharamukha', 'services.xml_generator', 'services.statement_validator', 'tenacity', 'h11', 'smmap', 'websockets', 'six', 'watchdog', 'idna', 'routes', 'cffi', 'Werkzeug', 'services', 'strategies.ContinuationChunk', 'proxy_tools', 'parsers.axis_parser', 'MarkupSafe', 'blinker', 'cryptography', 'jinja2', 'bottle', 'services.pdf_reader', 'jsonschema-specifications', 'anyio', 'language_data', 'werkzeug', 'services.xml_generator_hybrid_parser', 'Flask', 'pyinstaller', 'openpyxl', 'fonttools', 'protobuf', 'multipart', 'pywin32-ctypes', 'parsers.hybrid_parser', 'pandas', 'regex', 'services.xlsx_viewer', 'pdfminer', 'rpds-py', 'pefile', 'click', 'slicers.BOB_slicing', 'itsdangerous', 'numpy', 'slicers.hybrid_parser_slicing', 'pycparser', 'services.cash_validator', 'slicers', 'pypdfium2', 'pdfplumber', 'slicers.SBI_slicing', 'slicers.Axis_slicing', 'routes_tally', 'gitdb', 'requests', 'certifi', 'flask_cors', 'jsonschema', 'colorama', 'dateutil', 'charset-normalizer', 'toml', 'services.cash_xml_generator', 'typing_extensions', 'pythonnet', 'Jinja2', 'wrapt', 'strategies.FirstChunk', 'git', 'et_xmlfile', 'narwhals', 'licensing', 'parsers.cash_parser', 'uvicorn', 'flask', 'strategies', 'pykakasi', 'cachetools', 'pyarrow', 'lxml', 'services.cash_xlsx_writer', 'parsers.router', 'PyYAML', 'starlette', 'strategies.WholeChunk', 'httptools', 'referencing', 'tzdata', 'urllib3', 'jaconv', 'clr_loader', 'packaging', 'Flask-Cors', 'webview', 'attrs', 'app_flask', 'Deprecated', 'langcodes', 'parsers.bob_parser', 'parsers.sbi_parser', 'pyinstaller-hooks-contrib', 'pillow', 'altgraph', 'marisa-trie']
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
