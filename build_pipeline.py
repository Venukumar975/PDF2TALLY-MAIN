import os
import subprocess
import shutil
import sys

def run_pipeline():
    # Base directories
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "pdf2tally3_backend"))
    
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
        
    # 3. Copy the packaged executable to the backend static folder
    print("[PIPELINE] Step 3: Copying packaged installer to backend website static folder...")
    src_exe = os.path.join(current_dir, "dist", "PDF2TALLY_TRAIL_1.0.0.exe")
    dst_exe = os.path.join(backend_dir, "static", "PDF2TALLY_TRAIL_1.0.0.exe")
    
    if not os.path.exists(src_exe):
        print(f"[PIPELINE] Error: Packaged executable not found at '{src_exe}'")
        sys.exit(1)
        
    if not os.path.exists(os.path.dirname(dst_exe)):
        try:
            os.makedirs(os.path.dirname(dst_exe), exist_ok=True)
        except Exception as e:
            print(f"[PIPELINE] Warning: Could not create backend static directory: {e}")
            
    try:
        shutil.copy2(src_exe, dst_exe)
        print(f"[PIPELINE] Successfully copied executable to: {dst_exe}")
    except Exception as e:
        print(f"[PIPELINE] Error: Failed to copy executable: {e}")
        sys.exit(1)
        
    print("[PIPELINE] PIPELINE RUN COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_pipeline()
