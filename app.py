import os
from flask import Flask
from core.config import load_config, get_qwen_token
from auth.browser_login import get_token_via_browser
from core.qwen_api import SimpleQwenAPI
from api import register_blueprints

def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # 1. Load environment variables
    load_config()
    
    # 2. Check for Qwen token
    token = get_qwen_token()
    
    if not token:
        token = get_token_via_browser()
        
    if not token:
        print("[Fatal Error] Could not obtain QWEN_TOKEN. Shutting down the application.")
        exit(1)
        
    # 3. Initialize the Qwen API session
    print("[System] Initializing Qwen API session with the provided token...")
    qwen_session = SimpleQwenAPI(token)
    app.config['QWEN_SESSION'] = qwen_session
    
    # 4. Register blueprints
    register_blueprints(app)

    @app.route('/', methods=['GET', 'HEAD'])
    def health_check():
        """Root endpoint for connectivity checks."""
        return "Qwen API Proxy is running", 200
    
    return app

if __name__ == '__main__':
    print("[System] Starting Qwen API Proxy...")
    app = create_app()
    print("[System] Server is running on port 5000...")
    app.run(port=5000, debug=False)
