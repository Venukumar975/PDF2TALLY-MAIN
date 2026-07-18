import os
import base64
import tempfile
import fitz
from flask import request, jsonify, session, send_file
from routes_base import routes_bp, FILE_CACHE
from services.logger import logger

# In-memory history cache to store PDF state snapshots for Undo operations.
# Maps browser session_id to a list of byte-snapshots.
REDACT_HISTORY = {}

def get_session_history():
    sid = session.get("redact_session_id")
    if not sid:
        import uuid
        sid = str(uuid.uuid4())
        session["redact_session_id"] = sid
    if sid not in REDACT_HISTORY:
        REDACT_HISTORY[sid] = []
    return REDACT_HISTORY[sid]

@routes_bp.route("/api/redact/upload", methods=["POST"])
def api_redact_upload():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400
    
    file = request.files["file"]
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "message": "File must be a PDF."}), 400
        
    try:
        # Save file to a temporary location
        temp_dir = tempfile.gettempdir()
        import uuid
        session_id = session.get("redact_session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            session["redact_session_id"] = session_id
            
        temp_path = os.path.join(temp_dir, f"redact_{session_id}.pdf")
        file.save(temp_path)
        
        session["redact_pdf_path"] = temp_path
        session["redact_original_filename"] = file.filename
        
        # Clear history
        history = get_session_history()
        history.clear()
        
        # Cache active pdf bytes
        with open(temp_path, "rb") as f:
            FILE_CACHE["last_cleaned_pdf_bytes"] = f.read()
        FILE_CACHE["last_cleaned_pdf_filename"] = file.filename
        
        # Load and get page count
        doc = fitz.open(temp_path)
        page_count = len(doc)
        doc.close()
        
        return jsonify({
            "success": True,
            "filename": file.filename,
            "page_count": page_count
        })
    except Exception as e:
        logger.error(f"Error in redact upload: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@routes_bp.route("/api/redact/page", methods=["GET"])
def api_redact_page():
    temp_path = session.get("redact_pdf_path")
    if not temp_path or not os.path.exists(temp_path):
        return jsonify({"success": False, "message": "No PDF loaded in session."}), 400
        
    try:
        page_num = int(request.args.get("page", 0))
        scale = float(request.args.get("scale", 1.5))
        
        doc = fitz.open(temp_path)
        if page_num < 0 or page_num >= len(doc):
            doc.close()
            return jsonify({"success": False, "message": "Invalid page number."}), 400
            
        page = doc[page_num]
        
        # Render page to PNG bytes
        mat = page.rotation_matrix * fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        
        # Get dimensions
        width_pts = page.rect.width
        height_pts = page.rect.height
        width_px = pix.width
        height_px = pix.height
        
        doc.close()
        
        base64_png = base64.b64encode(png_bytes).decode("utf-8")
        
        return jsonify({
            "success": True,
            "image": f"data:image/png;base64,{base64_png}",
            "width_pts": width_pts,
            "height_pts": height_pts,
            "width_px": width_px,
            "height_px": height_px
        })
    except Exception as e:
        logger.error(f"Error rendering page: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@routes_bp.route("/api/redact/remove", methods=["POST"])
def api_redact_remove():
    temp_path = session.get("redact_pdf_path")
    if not temp_path or not os.path.exists(temp_path):
        return jsonify({"success": False, "message": "No PDF loaded in session."}), 400
        
    try:
        data = request.get_json(silent=True) or {}
        page_num = int(data.get("page", 0))
        x0 = float(data.get("x0"))
        y0 = float(data.get("y0"))
        x1 = float(data.get("x1"))
        y1 = float(data.get("y1"))
        scale = float(data.get("scale", 1.5))
        
        doc = fitz.open(temp_path)
        page = doc[page_num]
        
        # 1. Save history state (bytes of the doc before modification)
        history = get_session_history()
        history.append(doc.write())
        if len(history) > 10:
            history.pop(0)
            
        # 2. Get rendering matrix to invert screen coordinates back to PDF points
        mat = page.rotation_matrix * fitz.Matrix(scale, scale)
        screen_rect = fitz.Rect(x0, y0, x1, y1)
        pdf_rect = screen_rect * ~mat
        
        # 3. Add and apply redaction (white fill color) to the entire selected area
        page.add_redact_annot(pdf_rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        # 4. Save document to a different temporary file first, then overwrite original
        import shutil
        fd_temp, save_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd_temp)
        
        doc.save(save_path, garbage=3, deflate=True)
        doc.close()
        
        shutil.move(save_path, temp_path)
        
        # Cache updated bytes
        with open(temp_path, "rb") as f:
            FILE_CACHE["last_cleaned_pdf_bytes"] = f.read()
        FILE_CACHE["last_cleaned_pdf_filename"] = session.get("redact_original_filename", "cleaned.pdf")
        
        # Render updated page
        doc = fitz.open(temp_path)
        page = doc[page_num]
        mat = page.rotation_matrix * fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        doc.close()
        
        base64_png = base64.b64encode(png_bytes).decode("utf-8")
        
        return jsonify({
            "success": True,
            "image": f"data:image/png;base64,{base64_png}",
            "can_undo": len(history) > 0
        })
    except Exception as e:
        logger.error(f"Error applying redaction in route: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@routes_bp.route("/api/redact/undo", methods=["POST"])
def api_redact_undo():
    temp_path = session.get("redact_pdf_path")
    if not temp_path or not os.path.exists(temp_path):
        return jsonify({"success": False, "message": "No PDF loaded in session."}), 400
        
    try:
        data = request.get_json(silent=True) or {}
        page_num = int(data.get("page", 0))
        scale = float(data.get("scale", 1.5))
        
        history = get_session_history()
        if not history:
            return jsonify({"success": False, "message": "Nothing to undo."}), 400
            
        prev_bytes = history.pop()
        
        # Write bytes back to temp file
        with open(temp_path, "wb") as f:
            f.write(prev_bytes)
            
        # Cache updated bytes
        FILE_CACHE["last_cleaned_pdf_bytes"] = prev_bytes
            
        # Render updated page
        doc = fitz.open(temp_path)
        page = doc[page_num]
        mat = page.rotation_matrix * fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        png_bytes = pix.tobytes("png")
        doc.close()
        
        base64_png = base64.b64encode(png_bytes).decode("utf-8")
        
        return jsonify({
            "success": True,
            "image": f"data:image/png;base64,{base64_png}",
            "can_undo": len(history) > 0
        })
    except Exception as e:
        logger.error(f"Error performing undo in route: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@routes_bp.route("/api/redact/use", methods=["POST"])
def api_redact_use():
    temp_path = session.get("redact_pdf_path")
    if not temp_path or not os.path.exists(temp_path):
        return jsonify({"success": False, "message": "No PDF loaded in session."}), 400
        
    try:
        # Cache the path of the cleaned PDF to be used during bank conversion
        with open(temp_path, "rb") as f:
            FILE_CACHE["last_cleaned_pdf_bytes"] = f.read()
        FILE_CACHE["last_cleaned_pdf_filename"] = session.get("redact_original_filename", "cleaned.pdf")
        
        return jsonify({
            "success": True,
            "filename": session.get("redact_original_filename")
        })
    except Exception as e:
        logger.error(f"Error setting use cached file: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@routes_bp.route("/api/redact/download", methods=["GET"])
def api_redact_download():
    temp_path = session.get("redact_pdf_path")
    if not temp_path or not os.path.exists(temp_path):
        return "No PDF loaded in session", 400
    try:
        filename = session.get("redact_original_filename", "cleaned.pdf")
        if filename.endswith(".pdf"):
            filename = filename[:-4] + "_cleaned.pdf"
        else:
            filename = filename + "_cleaned.pdf"
            
        return send_file(
            temp_path,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )
    except Exception as e:
        logger.error(f"Error in downloading: {e}")
        return str(e), 500

@routes_bp.route("/api/redact/cleanup", methods=["POST"])
def api_redact_cleanup():
    try:
        temp_path = session.pop("redact_pdf_path", None)
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
            
        session.pop("redact_original_filename", None)
        
        # Clear in-memory history cache
        history = get_session_history()
        history.clear()
        
        # Clear active cleaned cache keys
        FILE_CACHE["last_cleaned_pdf_bytes"] = None
        FILE_CACHE["last_cleaned_pdf_filename"] = None
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
