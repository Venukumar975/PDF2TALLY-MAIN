import os
import sys
import threading
import time
import socket
import webview
from app_flask import app

# 1. Force the current execution path to the PyInstaller extraction directory if bundled
if hasattr(sys, '_MEIPASS'):
    os.chdir(sys._MEIPASS)

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
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def run_flask_backend(port):
    """Runs the Flask backend server on the chosen port."""
    try:
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Error starting backend: {e}")

def monitor_and_load_app(window, port):
    """Monitors the local Flask port and loads the root URL when it becomes online."""
    timeout = 15
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                window.load_url(f"http://127.0.0.1:{port}/")
                return
        except (OSError, ConnectionRefusedError):
            time.sleep(0.3)
            
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

    webview.start()