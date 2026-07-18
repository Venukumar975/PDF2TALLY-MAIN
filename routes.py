# routes.py
# Main routing interface - imports and exposes all sub-route blueprints.
from routes_base import routes_bp

# Import sub-route files to register endpoints on the blueprint
import routes_licensing
import routes_bank
import routes_gstr1
import routes_hybrid
import routes_download
import routes_tally
import routes_redact
