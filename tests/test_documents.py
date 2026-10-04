import os, io
from services.document_processor import process_document

def test_document_processing_pdf_native(app, sample_pdf_bytes):
    tmp_path = os.path.join(app.config['UPLOAD_FOLDER'], "test_proc.pdf")
    with open(tmp_path, "wb") as f:
        f.write(sample_pdf_bytes)

    res = process_document(tmp_path, "test_proc.pdf")
    assert res['success'] is True
    assert res['file_type'] == 'PDF'
    assert 'EMPLOYMENT' in res['extracted_text'] or 'CONTRACT' in res['extracted_text']
    assert res['word_count'] > 0

def test_document_processing_docx(app, sample_docx_bytes):
    tmp_path = os.path.join(app.config['UPLOAD_FOLDER'], "test_proc.docx")
    with open(tmp_path, "wb") as f:
        f.write(sample_docx_bytes)

    res = process_document(tmp_path, "test_proc.docx")
    assert res['success'] is True
    assert res['file_type'] == 'DOCX'
    assert 'NON-DISCLOSURE' in res['extracted_text']

def test_document_processing_txt(app, sample_txt_bytes):
    tmp_path = os.path.join(app.config['UPLOAD_FOLDER'], "test_proc.txt")
    with open(tmp_path, "wb") as f:
        f.write(sample_txt_bytes)

    res = process_document(tmp_path, "test_proc.txt")
    assert res['success'] is True
    assert res['file_type'] == 'TXT'
    assert 'COMMERCIAL SERVICES AGREEMENT' in res['extracted_text']

def test_document_processing_image_ocr(app, sample_png_bytes):
    tmp_path = os.path.join(app.config['UPLOAD_FOLDER'], "test_proc.png")
    with open(tmp_path, "wb") as f:
        f.write(sample_png_bytes)

    res = process_document(tmp_path, "test_proc.png")
    assert res['success'] is True
    assert res['file_type'] == 'IMAGE'
    assert res['is_scanned'] is True
    assert 'INVOICE' in res['extracted_text'] or len(res['extracted_text']) > 0

def test_view_document_page(auth_client, sample_txt_bytes):
    up_res = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'my_doc.txt')
    })
    doc_id = up_res.get_json()['data']['document_id']

    page_res = auth_client.get(f'/document/{doc_id}')
    assert page_res.status_code == 200
    assert 'my_doc.txt' in page_res.text
    assert 'Executive Summary' in page_res.text
    assert 'Important Dates' in page_res.text

def test_download_original(auth_client, sample_txt_bytes):
    up_res = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'original.txt')
    })
    doc_id = up_res.get_json()['data']['document_id']

    dl_res = auth_client.get(f'/document/{doc_id}/download')
    assert dl_res.status_code == 200
    assert 'attachment' in dl_res.headers.get('Content-Disposition', '')
    assert 'original.txt' in dl_res.headers.get('Content-Disposition', '')
    assert b'COMMERCIAL SERVICES AGREEMENT' in dl_res.data

def test_preview_original(auth_client, sample_txt_bytes):
    up_res = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'preview_doc.txt')
    })
    doc_id = up_res.get_json()['data']['document_id']

    prev_res = auth_client.get(f'/document/{doc_id}/preview')
    assert prev_res.status_code == 200
    assert 'inline' in prev_res.headers.get('Content-Disposition', '')
    assert b'COMMERCIAL SERVICES AGREEMENT' in prev_res.data

def test_export_txt(auth_client, sample_txt_bytes):
    up_res = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'export_test.txt')
    })
    doc_id = up_res.get_json()['data']['document_id']

    exp_res = auth_client.get(f'/document/{doc_id}/export/txt')
    assert exp_res.status_code == 200
    assert 'text/plain' in exp_res.headers.get('Content-Type', '')
    assert b'EXECUTIVE SUMMARY' in exp_res.data
    assert b'DISCLAIMER' in exp_res.data

def test_export_pdf(auth_client, sample_txt_bytes):
    up_res = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'export_test.txt')
    })
    doc_id = up_res.get_json()['data']['document_id']

    exp_res = auth_client.get(f'/document/{doc_id}/export/pdf')
    assert exp_res.status_code == 200
    assert 'application/pdf' in exp_res.headers.get('Content-Type', '')
    assert len(exp_res.data) > 500

def test_export_docx(auth_client, sample_txt_bytes):
    up_res = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'export_test.txt')
    })
    doc_id = up_res.get_json()['data']['document_id']

    exp_res = auth_client.get(f'/document/{doc_id}/export/docx')
    assert exp_res.status_code == 200
    assert len(exp_res.data) > 500

def test_list_documents_filtering_and_sorting(auth_client, sample_pdf_bytes, sample_docx_bytes, sample_txt_bytes):
    auth_client.post('/api/documents/upload', data={'file': (io.BytesIO(sample_pdf_bytes), 'contract_alpha.pdf')})
    auth_client.post('/api/documents/upload', data={'file': (io.BytesIO(sample_docx_bytes), 'nda_beta.docx')})
    auth_client.post('/api/documents/upload', data={'file': (io.BytesIO(sample_txt_bytes), 'agreement_gamma.txt')})

    # Test all
    res_all = auth_client.get('/api/documents')
    assert res_all.status_code == 200
    docs = res_all.get_json()['data']
    assert len(docs) >= 3

    # Test filter by PDF
    res_pdf = auth_client.get('/api/documents?type=PDF')
    pdf_docs = res_pdf.get_json()['data']
    assert all(d['file_type'] == 'PDF' for d in pdf_docs)
    assert any(d['original_filename'] == 'contract_alpha.pdf' for d in pdf_docs)

    # Test search query
    res_search = auth_client.get('/api/documents?q=alpha')
    search_docs = res_search.get_json()['data']
    assert len(search_docs) == 1
    assert search_docs[0]['original_filename'] == 'contract_alpha.pdf'

    # Test sort name_asc
    res_sort = auth_client.get('/api/documents?sort=name_asc')
    names = [d['original_filename'] for d in res_sort.get_json()['data']]
    assert names == sorted(names, key=str.lower)
