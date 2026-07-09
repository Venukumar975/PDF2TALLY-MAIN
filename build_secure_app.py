import os
import sys
import shutil
import subprocess
import codecs
import PyInstaller.__main__

def build_secure():
    print("[BUILD] Starting secure obfuscation build pipeline...")
    
    # 1. Clean previous build folders
    folders_to_clean = ["obf_dist", "build", "dist"]
    for folder in folders_to_clean:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"[BUILD] Cleaned folder: {folder}")
            except Exception as e:
                print(f"[BUILD] Warning: Could not remove folder {folder}: {e}")

    # 2. Run PyArmor to obfuscate all scripts recursively
    print("[BUILD] Running PyArmor obfuscation...")
    pyarmor_cmd = [
        sys.executable, "-m", "pyarmor.cli", "gen",
        "-O", "obf_dist",
        "-r",
        "desktop_run.py", "app_flask.py", "routes.py", "routes_tally.py", "licensing.py",
        "services", "parsers", "strategies", "slicers"
    ]
    
    try:
        result = subprocess.run(pyarmor_cmd, check=True, capture_output=True, text=True)
        print("[BUILD] PyArmor obfuscation completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[BUILD] CRITICAL ERROR: PyArmor failed!\nStdout: {e.stdout}\nStderr: {e.stderr}")
        sys.exit(1)

    # 3. Read requirements.txt to dynamically extract hidden imports
    hidden_imports = [
        "click",
        "jinja2",
        "werkzeug",
        "flask",
        "requests",
        "flask_cors",
        "webview",
        "pdfminer",
        "git",
        "dateutil"
    ]

    # Map package names to import names
    package_mappings = {
        "pywebview": "webview",
        "pdfminer.six": "pdfminer",
        "gitpython": "git",
        "python-dateutil": "dateutil",
        "python-multipart": "multipart"
    }

    if os.path.exists("requirements.txt"):
        try:
            with open("requirements.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            try:
                with codecs.open("requirements.txt", "r", "utf-16le") as f:
                    lines = f.readlines()
            except Exception:
                lines = []
                
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                mod_name = line.split("==")[0].split(">=")[0].split("<=")[0].strip()
                mod_name = mod_name.lstrip('\ufeff')
                
                # Apply mapping translation if exists
                import_name = package_mappings.get(mod_name.lower(), mod_name)
                
                if import_name and import_name not in ["streamlit", "pyarmor", "pyarmor.cli.core"]:
                    hidden_imports.append(import_name)

    # Append local obfuscated modules to prevent ModuleNotFoundError due to PyArmor encryption
    local_hidden_imports = ["app_flask", "routes", "routes_tally", "licensing"]
    local_dirs = ["services", "parsers", "strategies", "slicers"]
    for folder in local_dirs:
        local_hidden_imports.append(folder)
        if os.path.exists(folder):
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        rel_path = os.path.relpath(os.path.join(root, file), os.getcwd())
                        mod_name = os.path.splitext(rel_path)[0].replace(os.sep, '.')
                        local_hidden_imports.append(mod_name)
    hidden_imports.extend(local_hidden_imports)

    # Deduplicate imports
    hidden_imports = list(set(hidden_imports))
    print(f"[BUILD] Identified {len(hidden_imports)} hidden imports for PyInstaller: {hidden_imports}")

    # 4. Run PyInstaller pointing to the obfuscated entry point
    print("[BUILD] Invoking PyInstaller compilation...")
    pyinstaller_args = [
        'obf_dist/desktop_run.py',
        '--name=pdf2tallyXML',
        '--clean',
        '--noconfirm',
        '--console',
        '--paths=obf_dist',  # Search obf_dist for imports first
        '--collect-all=pdfplumber',
        '--collect-all=pypdfium2',
        '--collect-all=flask',
        '--collect-all=aksharamukha',
        '--add-data=templates;templates',
        '--add-data=static;static',
        '--add-data=telugu_mappings.json;.',
    ] + [f'--hidden-import={imp}' for imp in hidden_imports]

    PyInstaller.__main__.run(pyinstaller_args)
    print("\n[BUILD] SECURE PRODUCTION BUILD COMPLETED SUCCESSFULLY!")
    print("[BUILD] Output executable is in: dist/pdf2tallyXML/pdf2tallyXML.exe")

if __name__ == "__main__":
    build_secure()
