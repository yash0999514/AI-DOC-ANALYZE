import os, uuid
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename
from routes.auth import login_required
from models import db, Document
from services.document_processor import process_document, allowed_file, detect_file_type
from services.ai_service import ai_service

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/documents/upload', methods=['POST'])
@login_required
def upload_document():
    user_id = session['user_id']

    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': {
                'code': 'NO_FILE',
                'message': 'No file part in the upload request.'
            }
        }), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({
            'success': False,
            'error': {
                'code': 'EMPTY_FILENAME',
                'message': 'No file selected for uploading.'
            }
        }), 400

    orig_filename = file.filename
    if not allowed_file(orig_filename):
        return jsonify({
            'success': False,
            'error': {
                'code': 'UNSUPPORTED_TYPE',
                'message': "That file type isn't supported. Please upload PDF, DOCX, TXT, JPG, or PNG."
            }
        }), 400

    # Read bytes to validate file size
    file_bytes = file.read()
    file_size = len(file_bytes)

    if file_size == 0:
        return jsonify({
            'success': False,
            'error': {
                'code': 'EMPTY_FILE',
                'message': "Uploaded file is empty (0 bytes). Please upload a valid document."
            }
        }), 400

    max_len = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
    if file_size > max_len:
        return jsonify({
            'success': False,
            'error': {
                'code': 'FILE_TOO_LARGE',
                'message': f"Your file exceeds the maximum allowed size of {max_len // (1024*1024)}MB."
            }
        }), 413

    # Generate secure filename with UUID prefix to prevent collisions
    safe_base = secure_filename(orig_filename)
    if not safe_base:
        safe_base = "uploaded_document"
    unique_prefix = uuid.uuid4().hex[:12]
    stored_filename = f"{unique_prefix}_{safe_base}"
    upload_dir = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, stored_filename)

    with open(file_path, 'wb') as f:
        f.write(file_bytes)

    # Process extraction
    proc_result = process_document(file_path, orig_filename)
    if not proc_result.get('success'):
        # Cleanup uploaded file on extraction failure
        if os.path.isfile(file_path):
            os.remove(file_path)
        return jsonify({
            'success': False,
            'error': {
                'code': 'EXTRACTION_FAILED',
                'message': proc_result.get('error', "We couldn't extract readable text from this document.")
            }
        }), 422

    extracted_text = proc_result.get('extracted_text', '')

    # Run AI analysis
    try:
        analysis = ai_service.analyze_document(extracted_text, filename=orig_filename)
    except Exception as e:
        print(f"[API Upload] AI Analysis error: {e}")
        analysis = {
            'document_type': detect_file_type(orig_filename),
            'summary': 'Document uploaded. AI analysis temporarily unavailable.',
            'analysis_engine': 'None'
        }

    # Save to database
    doc = Document(
        user_id=user_id,
        original_filename=orig_filename,
        stored_filename=stored_filename,
        file_type=proc_result.get('file_type', detect_file_type(orig_filename)),
        file_size=file_size,
        extracted_text=extracted_text,
        status='analyzed'
    )
    doc.set_analysis(analysis)

    db.session.add(doc)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Document uploaded and analyzed successfully.',
        'data': {
            'document_id': doc.id,
            'redirect_url': f'/document/{doc.id}',
            'document': doc.to_dict()
        }
    }), 201

@api_bp.route('/documents', methods=['GET'])
@login_required
def list_documents():
    user_id = session['user_id']
    query_text = (request.args.get('q') or '').strip().lower()
    type_filter = (request.args.get('type') or '').strip().upper()
    sort_order = (request.args.get('sort') or 'newest').strip().lower()

    docs = Document.query.filter_by(user_id=user_id).all()

    # Filter by search query
    if query_text:
        docs = [
            d for d in docs
            if query_text in d.original_filename.lower() or
               (d.summary and query_text in d.summary.lower()) or
               query_text in d.file_type.lower()
        ]

    # Filter by file type
    if type_filter and type_filter != 'ALL':
        if type_filter == 'IMAGES':
            docs = [d for d in docs if d.file_type == 'IMAGE']
        else:
            docs = [d for d in docs if d.file_type == type_filter]

    # Sort
    if sort_order == 'oldest':
        docs.sort(key=lambda d: d.created_at)
    elif sort_order == 'name_asc':
        docs.sort(key=lambda d: d.original_filename.lower())
    elif sort_order == 'name_desc':
        docs.sort(key=lambda d: d.original_filename.lower(), reverse=True)
    else:  # newest
        docs.sort(key=lambda d: d.created_at, reverse=True)

    return jsonify({
        'success': True,
        'data': [d.to_dict() for d in docs],
        'count': len(docs)
    })

@api_bp.route('/documents/<int:doc_id>', methods=['GET'])
@login_required
def get_document(doc_id):
    user_id = session['user_id']
    doc = Document.query.get_or_404(doc_id)
    if doc.user_id != user_id:
        return jsonify({
            'success': False,
            'error': {'code': 'FORBIDDEN', 'message': 'You do not have access to this document.'}
        }), 403

    return jsonify({
        'success': True,
        'data': doc.to_dict(include_text=True)
    })

@api_bp.route('/documents/<int:doc_id>', methods=['DELETE'])
@login_required
def delete_document(doc_id):
    user_id = session['user_id']
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': 'Document not found.'}
        }), 404

    if doc.user_id != user_id:
        return jsonify({
            'success': False,
            'error': {'code': 'FORBIDDEN', 'message': 'You are not authorized to delete this document.'}
        }), 403

    # Delete physical file
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], doc.stored_filename)
    if os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"[API Delete] Warning: failed to delete physical file {file_path}: {e}")

    # Delete from database
    db.session.delete(doc)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f"Document '{doc.original_filename}' and its analysis were permanently deleted."
    })

@api_bp.route('/documents/<int:doc_id>/ask', methods=['POST'])
@login_required
def ask_document(doc_id):
    user_id = session['user_id']
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({
            'success': False,
            'error': {'code': 'NOT_FOUND', 'message': 'Document not found.'}
        }), 404

    if doc.user_id != user_id:
        return jsonify({
            'success': False,
            'error': {'code': 'FORBIDDEN', 'message': 'You are not authorized to query this document.'}
        }), 403

    data = request.get_json(silent=True) or request.form
    question = (data.get('question') or data.get('prompt') or '').strip()

    if not question:
        return jsonify({
            'success': False,
            'error': {'code': 'EMPTY_QUESTION', 'message': 'Please provide a non-empty question.'}
        }), 400

    history = data.get('history') or []

    qa_result = ai_service.ask_question(doc.extracted_text or '', question, conversation_history=history)
    if not qa_result.get('success'):
        return jsonify({
            'success': False,
            'error': {'code': 'AI_ERROR', 'message': qa_result.get('error', 'Failed to generate answer.')}
        }), 500

    return jsonify({
        'success': True,
        'data': {
            'document_id': doc.id,
            'question': question,
            'answer': qa_result.get('answer'),
            'model': qa_result.get('model')
        }
    })
