import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Retrieve configuration from environment or default to local 5000
    port = int(os.getenv("FLASK_PORT", 5001))
    # Run in debug mode locally
    app.run(host="127.0.0.1", port=port, debug=True)
