import os
import logging
from flask import Flask, request, redirect, url_for, session

# Import core licensing modules
import licensing

# Import custom logger
from services.logger import logger

# Import routes and cache/conversion storage from decoupled routes file
from routes import routes_bp, FILE_CACHE, LAST_CONVERSION

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "PDF2TALLY_FLASK_SESSION_SECRET_KEY_!"

# Register the routes blueprint
app.register_blueprint(routes_bp)

@app.before_request
def check_license():
    """
    Middleware verifying offline activation status before handling any request.
    Bypasses static assets, activation status checks, and license activation API.
    """
    allowed_paths = [
        "/activate",
        "/api/status",
        "/api/activate",
        "/api/admin/",
        "/api/register_request",
        "/static/",
        "/favicon.ico"
    ]
    if any(request.path.startswith(p) for p in allowed_paths):
        return None
        
    if session.get("logged_out"):
        return redirect("/activate")
        
    status = licensing.check_activation()
    if not status["activated"]:
        # Redirect to local license activation form
        return redirect("/activate")
    return None

if __name__ == "__main__":
    # Choose a free port dynamically
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    
    logger.info(f"Starting Flask server on local port {port}...")
    app.run(host="127.0.0.1", port=port, debug=False)
