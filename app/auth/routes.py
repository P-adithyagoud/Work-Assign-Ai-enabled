import functools
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.before_app_request
def load_logged_in_user():
    """Load the logged-in user details into flask.g before handling any request."""
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
    else:
        try:
            db = get_db()
            response = db.table('users').select('*').eq('id', user_id).execute()
            g.user = response.data[0] if response.data else None
        except Exception:
            g.user = None

def login_required(view):
    """View decorator that redirects anonymous users to the login page."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view

@bp.route('/signup', methods=('GET', 'POST'))
def signup():
    """Handle new user registration."""
    if g.user:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        db = get_db()
        error = None

        if not username:
            error = 'Username is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        else:
            try:
                # Check if username or email already exists
                response = db.table('users').select('id').or_(f"username.eq.{username},email.eq.{email}").execute()
                user_exists = response.data[0] if response.data else None
                
                if user_exists:
                    error = 'Username or email is already registered.'
            except Exception as e:
                error = f"Database connection error: {str(e)}"

        if error is None:
            try:
                db.table('users').insert({
                    'username': username,
                    'email': email,
                    'password_hash': generate_password_hash(password)
                }).execute()
                
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('auth.login'))
            except Exception as e:
                error = f"An database error occurred: {str(e)}"
                
        flash(error, 'error')

    return render_template('auth/signup.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    """Handle user login and session creation."""
    if g.user:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        login_id = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        
        db = get_db()
        error = None
        
        try:
            # Allow logging in with either username or email
            response = db.table('users').select('*').or_(f"username.eq.{login_id},email.eq.{login_id}").execute()
            user = response.data[0] if response.data else None

            if user is None:
                error = 'Incorrect username/email or password.'
            elif not check_password_hash(user['password_hash'], password):
                error = 'Incorrect username/email or password.'

            if error is None:
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash(f"Welcome back, {user['username']}!", 'success')
                return redirect(url_for('dashboard.index'))
                
        except Exception as e:
            error = f"Database error: {str(e)}"

        flash(error, 'error')

    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    """Clear session data and log out the user."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
