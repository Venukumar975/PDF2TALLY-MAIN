# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('parsers', 'parsers'), ('services', 'services'), ('strategies', 'strategies'), ('slicers', 'slicers'), ('templates', 'templates'), ('static', 'static'), ('telugu_mappings.json', '.')]
binaries = []
hiddenimports = ['et_xmlfile', 'typing_extensions', 'uvicorn', 'click', 'starlette', 'toml', 'rpds-py', 'pythonnet', 'MarkupSafe', 'clr_loader', 'Deprecated', 'openpyxl', 'pycparser', 'packaging', 'bottle', 'pywebview', 'regex', 'pdfplumber', 'language_data', 'certifi', 'setuptools', 'lxml', 'jsonschema', 'aksharamukha', 'marisa-trie', 'fonttools', 'watchdog', 'cachetools', 'numpy', 'httptools', 'pyinstaller', 'jinja2', 'cffi', 'werkzeug', 'pydeck', 'idna', 'python-dateutil', 'flask', 'anyio', 'cryptography', 'six', 'langcodes', 'h11', 'urllib3', 'pyinstaller-hooks-contrib', 'GitPython', 'Jinja2', 'altgraph', 'referencing', 'pandas', 'wrapt', 'smmap', 'requests', 'plotly', 'blinker', 'pypdfium2', 'pywin32-ctypes', 'colorama', 'gitdb', 'PyYAML', 'python-multipart', 'pykakasi', 'websockets', 'pdfminer.six', 'pefile', 'pillow', 'altair', 'tenacity', 'jsonschema-specifications', 'protobuf', 'tzdata', 'charset-normalizer', 'itsdangerous', 'narwhals', 'pyarrow', 'attrs', 'unicodedata2', 'proxy_tools', 'jaconv']
tmp_ret = collect_all('pdfplumber')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pypdfium2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('flask')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('aksharamukha')
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
