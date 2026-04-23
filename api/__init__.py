from flask import Flask
from .openai_routes import openai_bp
from .claude_routes import claude_bp
from .models_routes import models_bp

def register_blueprints(app: Flask):
    app.register_blueprint(openai_bp)
    app.register_blueprint(claude_bp)
    app.register_blueprint(models_bp)
