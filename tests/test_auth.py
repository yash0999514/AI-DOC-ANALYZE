def test_registration_success(client):
    res = client.post('/register', json={
        'username': 'john_doe',
        'email': 'john@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data['success'] is True
    assert data['data']['username'] == 'john_doe'

def test_registration_duplicate_username(client):
    client.post('/register', json={
        'username': 'unique_user',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    res = client.post('/register', json={
        'username': 'unique_user',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert res.status_code == 400
    data = res.get_json()
    assert data['success'] is False
    assert 'already taken' in data['error']['message']

def test_registration_short_password(client):
    res = client.post('/register', json={
        'username': 'short_pw_user',
        'password': '123',
        'confirm_password': '123'
    })
    assert res.status_code == 400
    data = res.get_json()
    assert data['success'] is False
    assert 'at least 6 characters' in data['error']['message']

def test_registration_mismatched_password(client):
    res = client.post('/register', json={
        'username': 'mismatch_user',
        'password': 'password123',
        'confirm_password': 'differentpassword'
    })
    assert res.status_code == 400
    data = res.get_json()
    assert data['success'] is False
    assert 'do not match' in data['error']['message']

def test_login_success(client):
    client.post('/register', json={
        'username': 'login_tester',
        'password': 'mypassword123',
        'confirm_password': 'mypassword123'
    })
    res = client.post('/login', json={
        'username': 'login_tester',
        'password': 'mypassword123'
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'Logged in' in data['message']

def test_login_wrong_password(client):
    client.post('/register', json={
        'username': 'wrong_pw_user',
        'password': 'correctpassword',
        'confirm_password': 'correctpassword'
    })
    res = client.post('/login', json={
        'username': 'wrong_pw_user',
        'password': 'incorrectpassword'
    })
    assert res.status_code == 401
    data = res.get_json()
    assert data['success'] is False
    assert 'Invalid username or password' in data['error']['message']

def test_login_nonexistent_user(client):
    res = client.post('/login', json={
        'username': 'ghost_user',
        'password': 'somepassword'
    })
    assert res.status_code == 401
    data = res.get_json()
    assert data['success'] is False

def test_logout(client):
    client.post('/register', json={
        'username': 'logout_user',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    res = client.post('/logout', json={})
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True

def test_protected_routes_unauthenticated(client):
    # API endpoints return 401 JSON
    res_api = client.get('/api/documents')
    assert res_api.status_code == 401
    data = res_api.get_json()
    assert data['success'] is False

    # HTML routes redirect to login
    res_page = client.get('/dashboard')
    assert res_page.status_code == 302
    assert '/login' in res_page.location
