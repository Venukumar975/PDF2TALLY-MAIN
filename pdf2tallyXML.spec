# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('parsers', 'parsers'), ('services', 'services'), ('strategies', 'strategies'), ('slicers', 'slicers'), ('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['marisa-trie', 'itsdangerous', 'click', 'proxy_tools', 'pyinstaller-hooks-contrib', 'pefile', 'Jinja2', 'httptools', 'PyYAML', 'gitdb', 'tzdata', 'langcodes', 'rpds-py', 'pyarrow', 'certifi', 'MarkupSafe', 'altgraph', 'packaging', 'pywin32-ctypes', 'narwhals', 'et_xmlfile', 'protobuf', 'setuptools', 'starlette', 'clr_loader', 'jsonschema', 'idna', 'werkzeug', 'cffi', 'cryptography', 'regex', 'referencing', 'python-multipart', 'fonttools', 'wrapt', 'python-dateutil', 'toml', 'pdfminer.six', 'lxml', 'websockets', 'cachetools', 'pillow', 'pdfplumber', 'anyio', 'smmap', 'altair', 'pyinstaller', 'requests', 'attrs', 'blinker', 'language_data', 'typing_extensions', 'bottle', 'pythonnet', 'six', 'charset-normalizer', 'unicodedata2', 'flask', 'jsonschema-specifications', 'watchdog', 'tenacity', 'pydeck', 'pypdfium2', 'uvicorn', 'GitPython', 'plotly', 'h11', 'jaconv', 'pycparser', 'colorama', 'pywebview', 'openpyxl', 'pykakasi', 'urllib3', 'aksharamukha', 'jinja2', 'numpy', 'pandas', 'Deprecated']
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
