import os, sys

# Ensure custom library path
if "/home/spark/pylib" not in sys.path:
    sys.path.insert(0, "/home/spark/pylib")

cwd = os.path.abspath(os.path.dirname(__file__)) if '__file__' in globals() else os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

try:
    import sitecustomize
except Exception:
    pass

from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import HTTPException
from config import config_by_name
from models import db
from routes import auth_bp, documents_bp, api_bp

def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
        if config_name not in config_by_name:
            config_name = 'default'

    app = Flask(
        __name__,
        static_folder='static',
        template_folder='templates'
    )

    app.config.from_object(config_by_name[config_name])

    # Ensure uploads and instance directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(api_bp)

    # Global context processor
    @app.context_processor
    def inject_globals():
        return {
            'app_name': app.config.get('APP_NAME', 'AI DOC'),
            'app_subtitle': app.config.get('APP_SUBTITLE', 'Intelligent Document Analysis'),
            'disclaimer': app.config.get('DISCLAIMER', 'AI-generated information is for understanding purposes only.')
        }

    # Error Handlers
    @app.errorhandler(404)
    def handle_404(e):
        if request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': {'code': 'NOT_FOUND', 'message': 'Resource not found.'}}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def handle_403(e):
        if request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': {'code': 'FORBIDDEN', 'message': 'Access forbidden.'}}), 403
        return render_template('errors/404.html', error_title="Forbidden (403)", error_message="You do not have permission to access this resource."), 403

    @app.errorhandler(413)
    def handle_413(e):
        if request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': {'code': 'FILE_TOO_LARGE', 'message': 'File exceeds maximum upload size.'}}), 413
        return render_template('errors/413.html'), 413

    @app.errorhandler(500)
    def handle_500(e):
        if request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': 'An internal server error occurred.'}}), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return e
        if request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': {'code': 'INTERNAL_ERROR', 'message': f'An unexpected server error occurred: {str(e)}'}}), 500
        return render_template('errors/500.html'), 500

    # Create tables
    with app.app_context():
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', False))
