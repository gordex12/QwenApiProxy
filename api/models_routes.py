import time
from flask import Blueprint, jsonify

models_bp = Blueprint('models', __name__)

@models_bp.route('/v1/models', methods=['GET'])
def list_models():
    available_models = [
        "qwen3.6-max-preview",
        "qwen3.6-plus",
        "qwen3.6-plus-preview",
        "qwen3.5-plus",
        "qwen3.5-omni-plus"
    ]
    
    data = []
    for model_name in available_models:
        data.append({
            "id": model_name,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "qwen"
        })
        
    return jsonify({
        "object": "list",
        "data": data
    })
