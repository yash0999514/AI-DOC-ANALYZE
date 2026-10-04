import io

def test_upload_valid_pdf(auth_client, sample_pdf_bytes):
    data = {
        'file': (io.BytesIO(sample_pdf_bytes), 'employment_contract.pdf')
    }
    res = auth_client.post('/api/documents/upload', data=data)
    assert res.status_code == 201
    res_data = res.get_json()
    assert res_data['success'] is True
    doc = res_data['data']['document']
    assert doc['file_type'] == 'PDF'
    assert doc['original_filename'] == 'employment_contract.pdf'
    assert doc['status'] == 'analyzed'

def test_upload_valid_docx(auth_client, sample_docx_bytes):
    data = {
        'file': (io.BytesIO(sample_docx_bytes), 'nda_agreement.docx')
    }
    res = auth_client.post('/api/documents/upload', data=data)
    assert res.status_code == 201
    res_data = res.get_json()
    assert res_data['success'] is True
    doc = res_data['data']['document']
    assert doc['file_type'] == 'DOCX'
    assert 'Non-Disclosure' in doc['summary'] or 'Agreement' in doc['summary'] or len(doc['summary']) > 0

def test_upload_valid_txt(auth_client, sample_txt_bytes):
    data = {
        'file': (io.BytesIO(sample_txt_bytes), 'commercial_terms.txt')
    }
    res = auth_client.post('/api/documents/upload', data=data)
    assert res.status_code == 201
    res_data = res.get_json()
    assert res_data['success'] is True
    doc = res_data['data']['document']
    assert doc['file_type'] == 'TXT'
    assert doc['analysis'] is not None

def test_upload_valid_png(auth_client, sample_png_bytes):
    data = {
        'file': (io.BytesIO(sample_png_bytes), 'invoice_scan.png')
    }
    res = auth_client.post('/api/documents/upload', data=data)
    assert res.status_code == 201
    res_data = res.get_json()
    assert res_data['success'] is True
    doc = res_data['data']['document']
    assert doc['file_type'] == 'IMAGE'

def test_upload_unsupported_file(auth_client):
    data = {
        'file': (io.BytesIO(b"alert('hello')"), 'malicious.js')
    }
    res = auth_client.post('/api/documents/upload', data=data)
    assert res.status_code == 400
    res_data = res.get_json()
    assert res_data['success'] is False
    assert "file type isn't supported" in res_data['error']['message']

def test_upload_empty_file(auth_client):
    data = {
        'file': (io.BytesIO(b""), 'empty_doc.txt')
    }
    res = auth_client.post('/api/documents/upload', data=data)
    assert res.status_code == 400
    res_data = res.get_json()
    assert res_data['success'] is False
    assert "empty" in res_data['error']['message']

def test_upload_oversized_file(auth_client):
    # App is configured with 4MB max content length in testing
    oversized = b"A" * (150 * 1024)
    data = {
        'file': (io.BytesIO(oversized), 'huge_file.txt')
    }
    res = auth_client.post('/api/documents/upload', data=data)
    assert res.status_code == 413
    res_data = res.get_json()
    assert res_data['success'] is False
    assert "exceeds" in res_data['error']['message'].lower() or "too_large" in res_data['error']['code'].lower()

def test_upload_unauthorized(client, sample_txt_bytes):
    data = {
        'file': (io.BytesIO(sample_txt_bytes), 'unauth.txt')
    }
    res = client.post('/api/documents/upload', data=data)
    assert res.status_code == 401
    res_data = res.get_json()
    assert res_data['success'] is False
