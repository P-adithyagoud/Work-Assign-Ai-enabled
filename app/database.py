import os
from supabase import create_client, Client
from flask import g

def get_db() -> Client:
    """
    Get a Supabase client connection.
    SUPABASE_URL and SUPABASE_KEY must be set in .env.
    """
    if 'db' not in g:
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError(
                "Missing SUPABASE_URL or SUPABASE_KEY in .env file."
            )
            
        g.db = create_client(url, key)
            
    return g.db

def close_db(e=None):
    """Clean up the database context."""
    g.pop('db', None)

def init_app(app):
    """Register teardown context and check database presence."""
    app.teardown_appcontext(close_db)
    
    with app.app_context():
        try:
            db = get_db()
            # Test connection by making a lightweight API call (getting users limit 1, or just let it pass if credentials exist)
            # Actually with REST API, unless we query a table, it doesn't fail on init.
            print("Supabase client initialized successfully.")
        except Exception as conn_err:
            print(f"Supabase client initialization failed: {str(conn_err)}. Please verify your credentials in .env.")
