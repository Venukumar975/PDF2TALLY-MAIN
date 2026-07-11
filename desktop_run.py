import os
import sys

# 1. Force the current execution path to the PyInstaller extraction directory if bundled
# This must run before importing any local modules to ensure relative paths resolve correctly.
if hasattr(sys, '_MEIPASS'):
    os.chdir(sys._MEIPASS)

def unblock_directory(directory):
    """Recursively removes the Zone.Identifier alternate data stream from all files in the directory."""
    if sys.platform != "win32":
        return
    try:
        unblocked_count = 0
        for root, _, files in os.walk(directory):
            for file in files:
                filepath = os.path.join(root, file)
                zone_stream = filepath + ":Zone.Identifier"
                try:
                    os.remove(zone_stream)
                    unblocked_count += 1
                except FileNotFoundError:
                    pass
                except Exception:
                    pass
        if unblocked_count > 0:
            print(f"[UNBLOCK] Successfully unblocked {unblocked_count} file(s) in {directory}", file=sys.stderr)
    except Exception as e:
        print(f"[UNBLOCK] Failed to unblock directory {directory}: {e}", file=sys.stderr)

# Run self-unblocking at startup on Windows to bypass internet download execution restrictions
if sys.platform == "win32":
    if hasattr(sys, '_MEIPASS'):
        unblock_directory(sys._MEIPASS)
    else:
        unblock_directory(os.path.dirname(os.path.abspath(__file__)))

import threading
import time
import socket
import webview
from app_flask import app
from services.logger import logger

def check_webview2_runtime():
    """Checks if Microsoft Edge WebView2 Runtime is installed on Windows."""
    if sys.platform != "win32":
        return True
    try:
        import winreg
        paths = [
            r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
            r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        ]
        for path in paths:
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
                        pv, _ = winreg.QueryValueEx(key, "pv")
                        if pv and pv != "0.0.0.0":
                            logger.info(f"Detected Microsoft Edge WebView2 Runtime version: {pv}")
                            return True
                except OSError:
                    pass
    except Exception as e:
        logger.warning(f"Error checking WebView2 Runtime in registry: {e}")
    return False

def show_error_dialog(title, message):
    """Displays a native system error dialog on Windows, or logs it on other platforms."""
    logger.error(f"Error Dialog [{title}]: {message}")
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
        except Exception as e:
            logger.error(f"Failed to display native Windows error dialog: {e}")

class WebviewApi:
    """API bridge class exposed to the PyWebView container for native operations."""
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def download_file(self, file_type):
        """
        Pops open a native OS save file dialog and writes the cached file bytes directly.
        Bypasses standard browser download restrictions in WebViews.
        """
        from app_flask import FILE_CACHE
        data = FILE_CACHE.get(file_type)
        filename = FILE_CACHE.get(f"{file_type}_filename", "output")
        
        if not data:
            return {"success": False, "message": "No file data found in cache. Run conversion first."}
            
        if 'xml' in file_type:
            file_types = ('XML files (*.xml)', 'All files (*.*)')
        elif 'json' in file_type:
            file_types = ('JSON files (*.json)', 'All files (*.*)')
        else:
            file_types = ('Excel workbooks (*.xlsx)', 'All files (*.*)')
        
        if not self._window:
            return {"success": False, "message": "WebView window not initialized."}
            
        save_path = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=filename,
            file_types=file_types
        )
        
        if save_path:
            if isinstance(save_path, (list, tuple)):
                if len(save_path) > 0:
                    save_path = save_path[0]
                else:
                    return {"success": False, "message": "Cancelled"}
            try:
                with open(save_path, "wb") as f:
                    f.write(data)
                return {"success": True, "path": save_path}
            except Exception as e:
                return {"success": False, "message": str(e)}
        return {"success": False, "message": "Save cancelled"}

def find_free_port():
    """Finds a free port on localhost dynamically."""
    logger.info("Scanning for a free local port...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    logger.info(f"Successfully allocated free local port: {port}")
    return port

def run_flask_backend(port):
    """Runs the Flask backend server on the chosen port."""
    try:
        logger.info(f"Starting Flask backend server on port {port}...")
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Critical error starting Flask backend: {e}", exc_info=True)

def monitor_and_load_app(window, port):
    """Monitors the local Flask port and loads the root URL when it becomes online."""
    timeout = 15
    start_time = time.time()
    logger.info(f"Starting monitoring thread for local server on port {port} (timeout: {timeout} seconds)...")
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                logger.info(f"Flask backend responding on port {port}. Loading server root URL in WebView window...")
                window.load_url(f"http://127.0.0.1:{port}/")
                return
        except (OSError, ConnectionRefusedError):
            time.sleep(0.3)
            
    logger.error("Initialization Timeout Error: Flask backend server failed to respond within 15 seconds.")
    error_html = """
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #0a0b10; color: #ef4444; text-align: center; padding-top: 150px;">
            <h2>❌ Initialization Timeout Error</h2>
            <p style="color: #9ca3af;">The local conversion engine failed to boot within 15 seconds.</p>
        </body>
    </html>
    """
    window.load_html(error_html)

if __name__ == "__main__":
    logger.info("Initializing Tally Automation Suite desktop container window...")
    import licensing
    logger.info(f"Final Compiled Machine Signature: {licensing.get_machine_signature()}")
    
    # Check WebView2 Runtime dependency on Windows
    if sys.platform == "win32":
        if not check_webview2_runtime():
            msg = (
                "Microsoft Edge WebView2 Runtime is missing on this computer.\n\n"
                "This runtime is required to display the application interface.\n"
                "Please download and install it from Microsoft's website:\n"
                "https://developer.microsoft.com/en-us/microsoft-edge/webview2/\n\n"
                "The application will now close."
            )
            logger.error("Startup aborted: WebView2 Runtime is not installed.")
            show_error_dialog("System Dependency Error", msg)
            sys.exit(1)

    local_port = find_free_port()

    # Create the API bridge object
    api_bridge = WebviewApi()

    backend_thread = threading.Thread(target=run_flask_backend, args=(local_port,), daemon=True)
    backend_thread.start()

    splash_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { 
                background-color: #0a0b10; 
                color: #ffffff; 
                font-family: sans-serif; 
                display: flex; 
                justify-content: center; 
                align-items: center; 
                height: 100vh; 
                margin: 0; 
            }
            .spinner { 
                border: 4px solid rgba(255, 255, 255, 0.05); 
                width: 50px; 
                height: 50px; 
                border-radius: 50%; 
                border-left-color: #8b5cf6; 
                animation: spin 1s linear infinite; 
                margin: 0 auto 20px auto; 
            }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        </style>
    </head>
    <body>
        <div style="text-align: center;">
            <div class="spinner"></div>
            <h2 style="font-weight: 500; font-family: 'Outfit', sans-serif;">Initializing Tally Automation Suite</h2>
            <p style="color: #6b7280; font-size: 0.9rem;">Configuring your secure offline accounting environment...</p>
        </div>
    </body>
    </html>
    """

    main_window = webview.create_window(
        title="Tally Automation Suite",
        html=splash_html,
        width=1280,
        height=850,
        resizable=True,
        js_api=api_bridge  # Expose JavaScript bridge
    )
    
    # Let the API bridge know about the window
    api_bridge.set_window(main_window)

    monitor_thread = threading.Thread(target=monitor_and_load_app, args=(main_window, local_port), daemon=True)
    monitor_thread.start()

    try:
        webview.start()
    except Exception as e:
        logger.exception("Critical error during PyWebView execution:")
        show_error_dialog(
            "Fatal Application Error",
            f"A critical error occurred while starting the desktop interface:\n\n{e}\n\nCheck app.log for more details."
        )
        sys.exit(1)