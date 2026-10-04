import io
from werkzeug.utils import secure_filename

def test_user_a_cannot_view_user_b_document(auth_client, other_user_client, sample_txt_bytes):
    # User A (alice) uploads document
    res_up = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'alice_private_contract.txt')
    })
    assert res_up.status_code == 201
    doc_id = res_up.get_json()['data']['document_id']

    # User B (bob) attempts to access via API
    res_b_api = other_user_client.get(f'/api/documents/{doc_id}')
    assert res_b_api.status_code == 403
    assert res_b_api.get_json()['success'] is False

    # User B attempts to access via HTML view
    res_b_view = other_user_client.get(f'/document/{doc_id}')
    assert res_b_view.status_code == 302 # Redirected away with error message
    assert '/dashboard' in res_b_view.location

def test_user_a_cannot_download_user_b_document(auth_client, other_user_client, sample_txt_bytes):
    res_up = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'confidential_alice.txt')
    })
    doc_id = res_up.get_json()['data']['document_id']

    # User B attempts to download
    res_dl = other_user_client.get(f'/document/{doc_id}/download')
    assert res_dl.status_code == 403

def test_user_a_cannot_export_user_b_document(auth_client, other_user_client, sample_txt_bytes):
    res_up = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'confidential_alice.txt')
    })
    doc_id = res_up.get_json()['data']['document_id']

    # User B attempts to export
    res_exp = other_user_client.get(f'/document/{doc_id}/export/pdf')
    assert res_exp.status_code == 403

def test_user_a_cannot_delete_user_b_document(auth_client, other_user_client, sample_txt_bytes):
    res_up = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'precious_alice.txt')
    })
    doc_id = res_up.get_json()['data']['document_id']

    # User B attempts to delete
    res_del = other_user_client.delete(f'/api/documents/{doc_id}')
    assert res_del.status_code == 403

    # Document should still exist for User A
    res_check = auth_client.get(f'/api/documents/{doc_id}')
    assert res_check.status_code == 200

def test_user_a_cannot_ask_question_about_user_b_document(auth_client, other_user_client, sample_txt_bytes):
    res_up = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'secret_alice.txt')
    })
    doc_id = res_up.get_json()['data']['document_id']

    # User B attempts to query User A's document
    res_ask = other_user_client.post(f'/api/documents/{doc_id}/ask', json={
        'question': 'What are the secrets?'
    })
    assert res_ask.status_code == 403

def test_owner_can_delete_own_document(auth_client, sample_txt_bytes):
    res_up = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'to_delete.txt')
    })
    doc_id = res_up.get_json()['data']['document_id']

    # Delete
    del_res = auth_client.delete(f'/api/documents/{doc_id}')
    assert del_res.status_code == 200
    assert del_res.get_json()['success'] is True

    # Check that it is gone
    get_res = auth_client.get(f'/api/documents/{doc_id}')
    assert get_res.status_code == 404

def test_secure_filename_path_traversal():
    assert secure_filename('../../../etc/passwd') == 'etc_passwd'
    assert secure_filename('..\\..\\windows\\system32') == 'windows_system32'
    assert secure_filename('/root/secret/contract.pdf') == 'root_secret_contract.pdf'
    assert secure_filename('file with spaces.docx') == 'file_with_spaces.docx'
