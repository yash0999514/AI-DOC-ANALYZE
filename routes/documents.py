import os, io, datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, abort, current_app
from routes.auth import login_required
from models import db, Document, User
from services.export_service import export_as_txt, export_as_pdf, export_as_docx

documents_bp = Blueprint('documents', __name__)

def format_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"

@documents_bp.route('/')
def index():
    user = None
    if session.get('user_id'):
        user = User.query.get(session['user_id'])
    return render_template('index.html', user=user)

@documents_bp.route('/about')
def about():
    user = None
    if session.get('user_id'):
        user = User.query.get(session['user_id'])
    return render_template('about.html', user=user)

@documents_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Fetch all documents belonging to this user
    user_docs = Document.query.filter_by(user_id=user_id).order_by(Document.created_at.desc()).all()
    
    # Calculate stats
    total_docs = len(user_docs)
    total_bytes = sum(d.file_size for d in user_docs)
    storage_formatted = format_file_size(total_bytes)
    
    now = datetime.datetime.utcnow()
    seven_days_ago = now - datetime.timedelta(days=7)
    recent_count = sum(1 for d in user_docs if d.created_at and d.created_at >= seven_days_ago)
    processing_count = sum(1 for d in user_docs if d.status in ('uploaded', 'processing'))
    
    stats = {
        'total': total_docs,
        'recent': recent_count,
        'processing': processing_count,
        'storage': storage_formatted
    }

    return render_template(
        'dashboard.html',
        user=user,
        documents=user_docs,
        stats=stats
    )

@documents_bp.route('/document/<int:doc_id>')
@login_required
def view_document(doc_id):
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    doc = Document.query.get_or_404(doc_id)
    if doc.user_id != user_id:
        flash("You are not authorized to view this document.", "error")
        return redirect(url_for('documents.dashboard'))

    analysis = doc.get_analysis()
    formatted_size = format_file_size(doc.file_size)

    return render_template(
        'document_view.html',
        user=user,
        document=doc,
        analysis=analysis,
        formatted_size=formatted_size
    )

@documents_bp.route('/document/<int:doc_id>/download')
@login_required
def download_original(doc_id):
    user_id = session['user_id']
    doc = Document.query.get_or_404(doc_id)
    if doc.user_id != user_id:
        abort(403, "Unauthorized to download this document.")

    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], doc.stored_filename)
    if not os.path.isfile(file_path):
        abort(404, "Original file not found on disk.")

    return send_file(file_path, as_attachment=True, download_name=doc.original_filename)

@documents_bp.route('/document/<int:doc_id>/preview')
@login_required
def preview_original(doc_id):
    user_id = session['user_id']
    doc = Document.query.get_or_404(doc_id)
    if doc.user_id != user_id:
        abort(403, "Unauthorized to preview this document.")

    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], doc.stored_filename)
    if not os.path.isfile(file_path):
        abort(404, "Original file not found on disk.")

    mimetype = 'application/pdf' if doc.file_type == 'PDF' else ('text/plain' if doc.file_type == 'TXT' else None)
    return send_file(file_path, as_attachment=False, mimetype=mimetype)

@documents_bp.route('/document/<int:doc_id>/export/<string:format_type>')
@login_required
def export_document(doc_id, format_type):
    user_id = session['user_id']
    doc = Document.query.get_or_404(doc_id)
    if doc.user_id != user_id:
        abort(403, "Unauthorized to export this document.")

    format_type = format_type.lower()
    analysis = doc.get_analysis()
    base_name = os.path.splitext(doc.original_filename)[0]

    if format_type == 'pdf':
        pdf_bytes = export_as_pdf(doc, analysis)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"{base_name}_analysis.pdf"
        )
    elif format_type == 'docx':
        docx_bytes = export_as_docx(doc, analysis)
        return send_file(
            io.BytesIO(docx_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=f"{base_name}_analysis.docx"
        )
    elif format_type == 'txt':
        txt_bytes = export_as_txt(doc, analysis)
        return send_file(
            io.BytesIO(txt_bytes),
            mimetype='text/plain',
            as_attachment=True,
            download_name=f"{base_name}_analysis.txt"
        )
    else:
        abort(400, f"Unsupported export format: {format_type}. Allowed: pdf, docx, txt.")
