import re
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, g
from models import db, User

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            if request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'UNAUTHORIZED',
                        'message': 'You need to sign in to access this resource.'
                    }
                }), 401
            flash('You need to sign in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.path))

        user = User.query.get(user_id)
        if not user:
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 'USER_NOT_FOUND',
                        'message': 'User session is invalid. Please log in again.'
                    }
                }), 401
            flash('Session expired. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))

        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if session.get('user_id'):
            return redirect(url_for('documents.dashboard'))
        return render_template('login.html')

    # POST
    data = request.get_json(silent=True) if request.is_json else request.form
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        err_msg = 'Please enter both username and password.'
        if request.is_json:
            return jsonify({'success': False, 'error': {'code': 'MISSING_FIELDS', 'message': err_msg}}), 400
        flash(err_msg, 'error')
        return render_template('login.html', username=username), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        err_msg = 'Invalid username or password. Please try again.'
        if request.is_json:
            return jsonify({'success': False, 'error': {'code': 'INVALID_CREDENTIALS', 'message': err_msg}}), 401
        flash(err_msg, 'error')
        return render_template('login.html', username=username), 401

    # Login successful
    session['user_id'] = user.id
    session['username'] = user.username

    next_url = request.args.get('next') or url_for('documents.dashboard')
    if request.is_json:
        return jsonify({
            'success': True,
            'message': 'Logged in successfully.',
            'redirect_url': next_url,
            'data': user.to_dict()
        })

    flash(f"Welcome back, {user.username}!", 'success')
    return redirect(next_url)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        if session.get('user_id'):
            return redirect(url_for('documents.dashboard'))
        return render_template('register.html')

    # POST
    data = request.get_json(silent=True) if request.is_json else request.form
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''
    confirm_password = data.get('confirm_password') or ''

    # Validation
    errors = []
    if not username:
        errors.append('Username is required.')
    elif len(username) < 3 or len(username) > 30:
        errors.append('Username must be between 3 and 30 characters.')
    elif not re.match(r'^[A-Za-z0-9_.-]+$', username):
        errors.append('Username can only contain letters, numbers, dots, and underscores.')

    if not password:
        errors.append('Password is required.')
    elif len(password) < 6:
        errors.append('Password must be at least 6 characters long.')

    if confirm_password and password != confirm_password:
        errors.append('Passwords do not match.')

    if not errors:
        existing = User.query.filter_by(username=username).first()
        if existing:
            errors.append('Username is already taken. Please choose another.')

    if errors:
        err_msg = ' '.join(errors)
        if request.is_json:
            return jsonify({'success': False, 'error': {'code': 'VALIDATION_FAILED', 'message': err_msg}}), 400
        for err in errors:
            flash(err, 'error')
        return render_template('register.html', username=username, email=email), 400

    # Create user
    user = User(username=username, email=email or None)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    # Log in user
    session['user_id'] = user.id
    session['username'] = user.username

    if request.is_json:
        return jsonify({
            'success': True,
            'message': 'Account created successfully!',
            'redirect_url': url_for('documents.dashboard'),
            'data': user.to_dict()
        }), 201

    flash('Account created successfully! Welcome to AI DOC.', 'success')
    return redirect(url_for('documents.dashboard'))

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    if request.is_json:
        return jsonify({'success': True, 'message': 'Logged out successfully.'})
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
