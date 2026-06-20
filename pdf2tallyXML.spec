# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('parsers', 'parsers'), ('services', 'services'), ('strategies', 'strategies'), ('slicers', 'slicers'), ('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['pythonnet', 'regex', 'rpds-py', 'pydeck', 'pycparser', 'werkzeug', 'setuptools', 'jaconv', 'click', 'cachetools', 'Deprecated', 'Jinja2', 'protobuf', 'websockets', 'pefile', 'charset-normalizer', 'idna', 'pdfplumber', 'aksharamukha', 'h11', 'openpyxl', 'requests', 'tzdata', 'tenacity', 'six', 'flask', 'watchdog', 'gitdb', 'pandas', 'jsonschema', 'cffi', 'altair', 'packaging', 'smmap', 'marisa-trie', 'uvicorn', 'toml', 'colorama', 'plotly', 'urllib3', 'et_xmlfile', 'bottle', 'wrapt', 'certifi', 'langcodes', 'MarkupSafe', 'python-multipart', 'language_data', 'jinja2', 'clr_loader', 'narwhals', 'pdfminer.six', 'referencing', 'starlette', 'attrs', 'lxml', 'pywin32-ctypes', 'altgraph', 'pykakasi', 'unicodedata2', 'PyYAML', 'python-dateutil', 'itsdangerous', 'numpy', 'cryptography', 'proxy_tools', 'pywebview', 'pypdfium2', 'typing_extensions', 'httptools', 'pyinstaller', 'anyio', 'pillow', 'blinker', 'pyarrow', 'pyinstaller-hooks-contrib', 'jsonschema-specifications', 'fonttools', 'GitPython']
tmp_ret = collect_all('pdfplumber')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pypdfium2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('flask')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['desktop_run.py'],
    pathex=[],
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
