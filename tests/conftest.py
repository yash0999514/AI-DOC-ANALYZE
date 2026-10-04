import sys, os, io, pytest
from PIL import Image, ImageDraw

if "/home/spark/pylib" not in sys.path:
    sys.path.insert(0, "/home/spark/pylib")

from app import create_app
from models import db, User, Document

@pytest.fixture
def app():
    # Use testing config with dedicated isolated test db
    test_db_path = "/home/spark/ai_doc_instance/test_ai_doc.db"
    if hasattr(db, '_conn') and db._conn:
        try:
            db._conn.close()
        except Exception:
            pass
        db._conn = None

    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass

    test_upload_dir = "/home/spark/ai_doc_instance/test_uploads"
    os.makedirs(test_upload_dir, exist_ok=True)

    os.environ['DATABASE_URL'] = "sqlite:///:memory:"
    os.environ['SECRET_KEY'] = 'test-secret-suite-key'
    os.environ['MAX_CONTENT_LENGTH'] = str(100 * 1024) # 4MB for tests

    app_instance = create_app('testing')
    app_instance.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"
    app_instance.config['UPLOAD_FOLDER'] = test_upload_dir
    app_instance.config['MAX_CONTENT_LENGTH'] = 100 * 1024

    with app_instance.app_context():
        db.create_all()
        yield app_instance
        db.drop_all()
        if hasattr(db, '_conn') and db._conn:
            try:
                db._conn.close()
            except Exception:
                pass
            db._conn = None

    # Clean up test uploads
    for f in os.listdir(test_upload_dir):
        try:
            os.remove(os.path.join(test_upload_dir, f))
        except Exception:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(app, client):
    # Register and login user 'alice'
    res = client.post('/register', json={
        'username': 'alice',
        'email': 'alice@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert res.status_code == 201
    return client

@pytest.fixture
def other_user_client(app):
    client = app.test_client()
    res = client.post('/register', json={
        'username': 'bob',
        'email': 'bob@example.com',
        'password': 'password456',
        'confirm_password': 'password456'
    })
    assert res.status_code == 201
    return client

@pytest.fixture
def sample_txt_bytes():
    text = """COMMERCIAL SERVICES AGREEMENT
This Commercial Agreement is entered into on January 15, 2026.
Effective Date: February 01, 2026.
Expiration Date: December 31, 2026.

Parties:
Alpha Tech Solutions LLC (Service Provider)
Global Commerce Corp (Client)

1. Obligations & Responsibilities
The Service Provider shall deliver quarterly security audits and maintain 99.9% uptime.
The Client shall pay all invoices within 30 days of receipt.

2. Penalties & Termination
Either party may terminate upon 30 days written notice. Failure to pay within 60 days constitutes a material breach and incurs a 5% monthly penalty.

3. Key Terms
"Confidential Information" means all non-public proprietary data.
"""
    return text.encode('utf-8')

@pytest.fixture
def sample_pdf_bytes():
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 750, "EMPLOYMENT CONTRACT AGREEMENT")
    c.drawString(100, 720, "Effective Date: March 01, 2026.")
    c.drawString(100, 690, "The Employee shall maintain strict confidentiality.")
    c.drawString(100, 660, "The Employer agrees to pay compensation bi-weekly.")
    c.drawString(100, 630, "Deadline for benefits enrollment: March 15, 2026.")
    c.save()
    buf.seek(0)
    return buf.getvalue()

@pytest.fixture
def sample_docx_bytes():
    import docx
    doc = docx.Document()
    doc.add_heading("NON-DISCLOSURE AGREEMENT", 0)
    doc.add_paragraph("Effective Date: April 10, 2026.")
    doc.add_paragraph("Recipient agrees not to disclose proprietary data.")
    doc.add_paragraph("Expiry Date: April 10, 2028.")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()

@pytest.fixture
def sample_png_bytes():
    img = Image.new('RGB', (500, 150), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((20, 30), "INVOICE #99812", fill=(0, 0, 0))
    d.text((20, 60), "Due Date: May 20, 2026", fill=(0, 0, 0))
    d.text((20, 90), "Amount Due: $1,250.00", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue()
