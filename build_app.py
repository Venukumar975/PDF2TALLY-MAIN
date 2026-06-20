import os
import PyInstaller.__main__

# 1. Read requirements.txt automatically to collect dependencies
hidden_imports = [
    "click",
    "jinja2",
    "werkzeug",
    "flask"
]

if os.path.exists("requirements.txt"):
    try:
        # Open requirements with UTF-16LE or default fallback
        import codecs
        with codecs.open("requirements.txt", "r", "utf-16le") as f:
            lines = f.readlines()
    except Exception:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            # Extract clean module name (e.g., pdfplumber from pdfplumber==0.11.9)
            mod_name = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
            # Strip UTF-16 BOM character if present
            mod_name = mod_name.lstrip('\ufeff')
            if mod_name and mod_name not in ["streamlit"]:  # Exclude Streamlit to keep build light
                hidden_imports.append(mod_name)

# Remove duplicates
hidden_imports = list(set(hidden_imports))

print(f"[BUILD] Found and verifying {len(hidden_imports)} modules from requirements.txt...")

# 2. Run PyInstaller to build a standalone desktop executable
PyInstaller.__main__.run([
    'desktop_run.py',
    '--name=pdf2tallyXML',
    '--clean',
    '--noconfirm',  # Overwrite output directory without confirmation
    '--console',  # Keep console open for diagnostics debugging
    '--collect-all=pdfplumber',
    '--collect-all=pypdfium2',
    '--collect-all=flask',
    '--add-data=parsers;parsers',
    '--add-data=services;services',
    '--add-data=strategies;strategies',
    '--add-data=slicers;slicers',
    '--add-data=templates;templates',
    '--add-data=static;static',
    '--add-data=telugu_mappings.json;.',
] + [f'--hidden-import={imp}' for imp in hidden_imports])