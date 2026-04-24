import time
import threading
from flask import Blueprint, jsonify

usage_bp = Blueprint('usage', __name__)

# Thread-safe in-memory usage tracker
_usage_lock = threading.Lock()
_usage_data = {
    "total_requests": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_images_uploaded": 0,
    "started_at": int(time.time()),
    "requests_by_endpoint": {
        "openai": 0,
        "claude": 0,
    }
}


def track_request(endpoint: str, input_tokens: int = 0, output_tokens: int = 0, images: int = 0):
    """Record usage metrics for a completed request."""
    with _usage_lock:
        _usage_data["total_requests"] += 1
        _usage_data["total_input_tokens"] += input_tokens
        _usage_data["total_output_tokens"] += output_tokens
        _usage_data["total_images_uploaded"] += images
        if endpoint in _usage_data["requests_by_endpoint"]:
            _usage_data["requests_by_endpoint"][endpoint] += 1


def get_usage_snapshot() -> dict:
    """Return a copy of the current usage data."""
    with _usage_lock:
        snapshot = dict(_usage_data)
        snapshot["requests_by_endpoint"] = dict(_usage_data["requests_by_endpoint"])
        snapshot["uptime_seconds"] = int(time.time()) - snapshot["started_at"]
        return snapshot


@usage_bp.route('/v1/usage', methods=['GET'])
def get_usage():
    """Return proxy usage statistics in a format compatible with monitoring dashboards."""
    snapshot = get_usage_snapshot()
    return jsonify({
        "object": "usage",
        "data": {
            "total_requests": snapshot["total_requests"],
            "total_input_tokens": snapshot["total_input_tokens"],
            "total_output_tokens": snapshot["total_output_tokens"],
            "total_tokens": snapshot["total_input_tokens"] + snapshot["total_output_tokens"],
            "total_images_uploaded": snapshot["total_images_uploaded"],
            "requests_by_endpoint": snapshot["requests_by_endpoint"],
            "uptime_seconds": snapshot["uptime_seconds"],
            "started_at": snapshot["started_at"]
        }
    })
