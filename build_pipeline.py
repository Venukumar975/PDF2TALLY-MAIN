import os
import subprocess
import shutil
import sys

def run_pipeline():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print("[PIPELINE] Starting complete build and packaging pipeline...")
    
    # 1. Run secure pyarmor obfuscated pyinstaller build
    print("[PIPELINE] Step 1: Running secure obfuscated PyInstaller build...")
    build_secure_script = os.path.join(current_dir, "build_secure_app.py")
    if not os.path.exists(build_secure_script):
        print(f"[PIPELINE] Error: Could not find '{build_secure_script}'")
        sys.exit(1)
        
    try:
        subprocess.run([sys.executable, build_secure_script], cwd=current_dir, check=True)
        print("[PIPELINE] Secure PyInstaller build completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[PIPELINE] Error: Secure PyInstaller build failed with exit code {e.returncode}")
        sys.exit(1)
        
    # 2. Compile the installer using Inno Setup
    print("[PIPELINE] Step 2: Compiling installer with Inno Setup...")
    iscc_path = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    iss_script = os.path.join(current_dir, "installer.iss")
    
    if not os.path.exists(iscc_path):
        print(f"[PIPELINE] Error: Inno Setup compiler not found at '{iscc_path}'")
        sys.exit(1)
    if not os.path.exists(iss_script):
        print(f"[PIPELINE] Error: Inno Setup script not found at '{iss_script}'")
        sys.exit(1)
        
    try:
        subprocess.run([iscc_path, iss_script], cwd=current_dir, check=True)
        print("[PIPELINE] Inno Setup compilation completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"[PIPELINE] Error: Inno Setup compilation failed with exit code {e.returncode}")
        sys.exit(1)
        
    print("[PIPELINE] PIPELINE RUN COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_pipeline()
