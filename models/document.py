import sys, os, datetime, json
if "/home/spark/pylib" not in sys.path:
    sys.path.insert(0, "/home/spark/pylib")

from models import db

class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    extracted_text = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default='uploaded')
    analysis_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def get_analysis(self) -> dict:
        if not self.analysis_json:
            return {}
        try:
            return json.loads(self.analysis_json)
        except Exception:
            return {}

    def set_analysis(self, analysis_dict: dict):
        if not isinstance(analysis_dict, dict):
            analysis_dict = {}
        self.analysis_json = json.dumps(analysis_dict, ensure_ascii=False, indent=2)
        if 'summary' in analysis_dict and analysis_dict['summary']:
            self.summary = analysis_dict['summary']
        self.status = 'analyzed'
        self.updated_at = datetime.datetime.utcnow()

    def to_dict(self, include_text: bool = False) -> dict:
        d = {
            'id': self.id,
            'user_id': self.user_id,
            'original_filename': self.original_filename,
            'stored_filename': self.stored_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'upload_date': self.upload_date.isoformat() if isinstance(self.upload_date, datetime.datetime) else str(self.upload_date),
            'summary': self.summary or '',
            'status': self.status,
            'analysis': self.get_analysis(),
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime.datetime) else str(self.created_at),
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime.datetime) else str(self.updated_at),
        }
        if include_text:
            d['extracted_text'] = self.extracted_text or ''
        return d

    def __repr__(self):
        return f"<Document {self.id}: {self.original_filename} ({self.status})>"
