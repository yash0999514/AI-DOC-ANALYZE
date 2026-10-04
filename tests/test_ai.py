import io, json
from services.ai_service import ai_service

def test_ai_service_missing_api_key_heuristic(sample_txt_bytes):
    # Temporarily ensure API key is unset
    orig_key = ai_service.api_key
    ai_service.api_key = ''
    try:
        text = sample_txt_bytes.decode('utf-8')
        analysis = ai_service.analyze_document(text, "commercial_terms.txt")
        assert analysis is not None
        assert 'Commercial Agreement' in analysis['summary'] or 'COMMERCIAL' in analysis['summary'] or len(analysis['summary']) > 0
        assert analysis['document_type'] in ['Legal Agreement / Contract', 'General Document']
        assert len(analysis['important_dates']) > 0
        assert any('2026' in d['date'] for d in analysis['important_dates'])
        assert len(analysis['obligations']) > 0
        assert 'Local Heuristic Intelligence Engine' in analysis['analysis_engine']
    finally:
        ai_service.api_key = orig_key

def test_ai_service_mocked_gemini_success(monkeypatch, sample_txt_bytes):
    mock_payload = {
        "document_type": "Commercial Services Agreement",
        "summary": "This contract specifies quarterly security audits provided by Alpha Tech Solutions to Global Commerce Corp.",
        "main_purpose": "To govern technology audit services and payment terms.",
        "key_points": [
            "Alpha Tech delivers quarterly security audits.",
            "Client must pay invoices within 30 days.",
            "30 days notice required for termination."
        ],
        "important_dates": [
            {"date": "February 01, 2026", "event": "Effective Date", "type": "Effective Date"},
            {"date": "December 31, 2026", "event": "Expiration Date", "type": "Expiration"}
        ],
        "parties_or_entities": [
            {"name": "Alpha Tech Solutions LLC", "role": "Service Provider", "type": "Organization"},
            {"name": "Global Commerce Corp", "role": "Client", "type": "Organization"}
        ],
        "obligations": [
            {"party": "Alpha Tech Solutions", "responsibility": "Deliver quarterly security audits."},
            {"party": "Global Commerce Corp", "responsibility": "Pay invoices within 30 days."}
        ],
        "risks_or_warnings": [
            {"title": "Late Payment Penalty", "severity": "Important", "description": "5% monthly penalty for payments overdue by 60 days."}
        ],
        "action_items": ["Set calendar reminder for Feb 1, 2026 effective date."],
        "simplified_explanation": "Alpha Tech checks security 4 times a year, and the client pays them on time.",
        "key_terms": [
            {"term": "Confidential Information", "explanation": "Private business and technical data."}
        ]
    }

    ai_service.api_key = 'fake-test-key'
    monkeypatch.setattr(ai_service, '_call_gemini_api', lambda prompt, system_instruction=None: json.dumps(mock_payload))

    text = sample_txt_bytes.decode('utf-8')
    res = ai_service.analyze_document(text, "commercial.txt")

    assert res['document_type'] == "Commercial Services Agreement"
    assert "Alpha Tech Solutions" in res['summary']
    assert len(res['important_dates']) == 2
    assert len(res['obligations']) == 2
    assert res['analysis_engine'] == "Gemini AI"

def test_ai_service_malformed_json_fallback(monkeypatch, sample_txt_bytes):
    ai_service.api_key = 'fake-test-key'
    # Return corrupt/invalid JSON
    monkeypatch.setattr(ai_service, '_call_gemini_api', lambda prompt, system_instruction=None: "Sorry, I can only provide text: { broken json ...")

    text = sample_txt_bytes.decode('utf-8')
    res = ai_service.analyze_document(text, "broken.txt")
    # Must not crash! Must fallback gracefully
    assert res is not None
    assert 'summary' in res
    assert len(res['summary']) > 0

def test_ai_service_api_failure_fallback(monkeypatch, sample_txt_bytes):
    ai_service.api_key = 'fake-test-key'
    def mock_fail(prompt, system_instruction=None):
        raise RuntimeError("Google API Rate limit or 503 Service Unavailable")

    monkeypatch.setattr(ai_service, '_call_gemini_api', mock_fail)

    text = sample_txt_bytes.decode('utf-8')
    res = ai_service.analyze_document(text, "test.txt")
    # Must not raise exception, must fallback to heuristic extraction
    assert res is not None
    assert len(res['summary']) > 0
    assert 'Gemini API fallback' in res['analysis_engine']

def test_qa_mocked_success(monkeypatch, auth_client, sample_txt_bytes):
    up_res = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'qa_doc.txt')
    })
    doc_id = up_res.get_json()['data']['document_id']

    ai_service.api_key = 'fake-key'
    monkeypatch.setattr(ai_service, '_call_gemini_api', lambda prompt, system_instruction=None: "The effective date of the agreement is February 01, 2026.")

    qa_res = auth_client.post(f'/api/documents/{doc_id}/ask', json={
        'question': 'When is the effective date?'
    })
    assert qa_res.status_code == 200
    data = qa_res.get_json()
    assert data['success'] is True
    assert 'February 01, 2026' in data['data']['answer']

def test_qa_empty_question(auth_client, sample_txt_bytes):
    up_res = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'qa_doc.txt')
    })
    doc_id = up_res.get_json()['data']['document_id']

    qa_res = auth_client.post(f'/api/documents/{doc_id}/ask', json={
        'question': '   '
    })
    assert qa_res.status_code == 400
    data = qa_res.get_json()
    assert data['success'] is False
    assert 'non-empty question' in data['error']['message']

def test_qa_offline_fallback(monkeypatch, auth_client, sample_txt_bytes):
    up_res = auth_client.post('/api/documents/upload', data={
        'file': (io.BytesIO(sample_txt_bytes), 'qa_doc.txt')
    })
    doc_id = up_res.get_json()['data']['document_id']

    # Unset API key to test document keyword search fallback
    orig_key = ai_service.api_key
    ai_service.api_key = ''
    try:
        qa_res = auth_client.post(f'/api/documents/{doc_id}/ask', json={
            'question': 'What are the obligations of the Service Provider?'
        })
        assert qa_res.status_code == 200
        data = qa_res.get_json()
        assert data['success'] is True
        assert 'quarterly security audits' in data['data']['answer']
    finally:
        ai_service.api_key = orig_key
