# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('parsers', 'parsers'), ('services', 'services'), ('strategies', 'strategies'), ('slicers', 'slicers'), ('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['typing_extensions', 'certifi', 'blinker', 'anyio', 'langcodes', 'cryptography', 'lxml', 'aksharamukha', 'altair', 'python-multipart', 'plotly', 'GitPython', 'pydeck', 'pdfminer.six', 'wrapt', 'urllib3', 'pdfplumber', 'jinja2', 'Jinja2', 'jsonschema', 'h11', 'fonttools', 'pyinstaller-hooks-contrib', 'unicodedata2', 'jsonschema-specifications', 'click', 'pywin32-ctypes', 'Deprecated', 'colorama', 'protobuf', 'starlette', 'six', 'et_xmlfile', 'marisa-trie', 'pefile', 'proxy_tools', 'watchdog', 'tenacity', 'setuptools', 'charset-normalizer', 'tzdata', 'werkzeug', 'clr_loader', 'toml', 'httptools', 'MarkupSafe', 'bottle', 'itsdangerous', 'regex', 'pillow', 'cachetools', 'cffi', 'idna', 'pythonnet', 'pyarrow', 'pywebview', 'pykakasi', 'pyinstaller', 'gitdb', 'openpyxl', 'uvicorn', 'referencing', 'python-dateutil', 'packaging', 'pycparser', 'PyYAML', 'narwhals', 'rpds-py', 'pandas', 'numpy', 'jaconv', 'altgraph', 'language_data', 'requests', 'smmap', 'websockets', 'pypdfium2', 'attrs', 'flask']
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
