import time
import uuid
import json
from flask import Blueprint, request, jsonify, Response, current_app

claude_bp = Blueprint('claude', __name__)

@claude_bp.route('/v1/messages', methods=['POST'])
def claude_messages():
    req = request.json
    anthropic_messages = req.get("messages", [])
    system_prompt = req.get("system", "")
    is_stream = req.get("stream", False)
    
    qwen_session = current_app.config['QWEN_SESSION']
    qwen_session.model = req.get("model", "qwen3.6-plus")
    
    if not anthropic_messages and not system_prompt:
        return jsonify({"error": {"type": "invalid_request_error", "message": "No messages provided"}}), 400
        
    print(f"[Claude API] New stateless request received with {len(anthropic_messages)} messages; stream={is_stream}")
    
    # Normalizing Claude-style messages to the format expected by the proxy (OpenAI-like)
    normalized_messages = []
    if system_prompt:
        normalized_messages.append({"role": "system", "content": system_prompt})
        
    for msg in anthropic_messages:
        role = msg.get("role", "user")
        raw_content = msg.get("content", "")
        if isinstance(raw_content, list):
            texts = [block.get("text", "") for block in raw_content if block.get("type", "") == "text"]
            content = " ".join(texts)
        else:
            content = raw_content
        normalized_messages.append({"role": role, "content": content})

    def generate_claude_stream():
        msg_id = f"msg_claude_{uuid.uuid4()}"
        model = req.get("model", "qwen")
        
        # The Anthropic client reads input_tokens on the FIRST chunk, but Qwen only sends it on the last one.
        # We will run an approximate heuristic of characters / 3.5 so the Client doesn't show 0.
        estimated_input_len = sum([len(m.get("content", "")) for m in normalized_messages])
        estimated_in_tokens = max(1, estimated_input_len // 3)
        
        # message_start
        yield f'event: message_start\ndata: {{"type": "message_start", "message": {{"id": "{msg_id}", "type": "message", "role": "assistant", "content": [], "model": "{model}", "stop_reason": null, "stop_sequence": null, "usage": {{"input_tokens": {estimated_in_tokens}, "output_tokens": 0}}}}}}\n\n'
        
        # content_block_start
        yield f'event: content_block_start\ndata: {{"type": "content_block_start", "index": 0, "content_block": {{"type": "text", "text": ""}}}}\n\n'
        
        started_thinking = False
        finished_thinking = False
        final_stream_usage = {}
        
        for chunk in qwen_session.send_message(normalized_messages):
            if "error" in chunk:
                error_payload = {
                    "type": "error",
                    "error": {"type": "api_error", "message": chunk["error"]}
                }
                yield f'event: error\ndata: {json.dumps(error_payload)}\n\n'
                break
                
            content = chunk.get("content", "")
            is_think = chunk.get("is_thinking", False)
            if chunk.get("usage"):
                final_stream_usage = chunk.get("usage")
                
            emit_content = ""
            if is_think:
                if not started_thinking:
                    emit_content += "<think>\n"
                    started_thinking = True
                emit_content += content
            else:
                if started_thinking and not finished_thinking:
                    emit_content += "\n</think>\n\n"
                    finished_thinking = True
                emit_content += content
                
            if emit_content:
                delta_payload = {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "text_delta",
                        "text": emit_content
                    }
                }
                yield f'event: content_block_delta\ndata: {json.dumps(delta_payload)}\n\n'

            if chunk.get("status") == "finished":
                pass
                
        # content_block_stop
        yield f'event: content_block_stop\ndata: {{"type": "content_block_stop", "index": 0}}\n\n'
        
        # message_delta
        output_tokens = final_stream_usage.get("output_tokens", 0)
        message_delta_payload = {
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {
                "input_tokens": final_stream_usage.get("input_tokens", 0),
                "output_tokens": final_stream_usage.get("output_tokens", 0)
            }
        }
        yield f'event: message_delta\ndata: {json.dumps(message_delta_payload)}\n\n'
        
        # message_stop
        yield f'event: message_stop\ndata: {{"type": "message_stop"}}\n\n'

    if is_stream:
        return Response(generate_claude_stream(), mimetype='text/event-stream')

    # Non-stream block
    full_text = ""
    start_think = False
    finish_think = False
    final_usage = {}
    
    for chunk in qwen_session.send_message(normalized_messages):
        if "error" in chunk:
            return jsonify({"error": {"type": "api_error", "message": chunk["error"]}}), 500
            
        content = chunk.get("content", "")
        if chunk.get("is_thinking"):
            if not start_think:
                full_text += "<think>\n"
                start_think = True
            full_text += content
        else:
            if start_think and not finish_think:
                full_text += "\n</think>\n\n"
                finish_think = True
            full_text += content
            
        if chunk.get("usage"):
            final_usage = chunk["usage"]

    response_data = {
        "id": f"msg_claude_{uuid.uuid4()}",
        "type": "message",
        "role": "assistant",
        "model": req.get("model", "qwen"),
        "content": [
            {
                "type": "text",
                "text": full_text
            }
        ],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {
            "input_tokens": final_usage.get("input_tokens", 0),
            "output_tokens": final_usage.get("output_tokens", 0)
        }
    }
    
    return jsonify(response_data)
