# routes_download.py
import io
from flask import send_file, jsonify
from routes_base import routes_bp, FILE_CACHE
from services.logger import logger

@routes_bp.route("/api/download/<file_type>", methods=["GET"])
def api_download(file_type):
    # Valid file types: "xml_bank", "xlsx_bank", "xml_cash", "xlsx_cash", "json_gstr1"
    if file_type not in FILE_CACHE or FILE_CACHE[file_type] is None:
        return f"<h3>Error: No generated output file found for Type '{file_type}'. Convert a statement first.</h3>", 404
        
    data = FILE_CACHE[file_type]
    filename = FILE_CACHE.get(f"{file_type}_filename", "output_file")
    
    if "xml" in file_type:
        mimetype = "application/xml"
    elif "json" in file_type:
        mimetype = "application/json"
    else:
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    return send_file(
        io.BytesIO(data),
        mimetype=mimetype,
        download_name=filename,
        as_attachment=True
    )


