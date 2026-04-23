import time
import uuid
import json
from flask import Blueprint, request, jsonify, Response, current_app

openai_bp = Blueprint('openai', __name__)

@openai_bp.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    req = request.json
    messages = req.get("messages", [])
    is_stream = req.get("stream", False)
    
    if not messages:
        return jsonify({"error": "No messages provided"}), 400
    
    print(f"[OpenAI API] New stateless request received with {len(messages)} messages; stream={is_stream}")
    
    qwen_session = current_app.config['QWEN_SESSION']
    
    # Generator that will consume Qwen stream chunks and format them into OpenAI format
    def generate_stream():
        chat_id = f"chatcmpl-{uuid.uuid4()}"
        created = int(time.time())
        model = req.get("model", "qwen")
        
        started_thinking = False
        finished_thinking = False
        final_stream_usage = {}

        for chunk in qwen_session.send_message(messages):
            if "error" in chunk:
                yield f'data: {{"error": "{chunk["error"]}"}}\n\n'
                break
                
            content = chunk.get("content", "")
            is_think = chunk.get("is_thinking", False)
            
            # Accumulate the latest usage received in case it is fragmented
            if chunk.get("usage"):
                final_stream_usage = chunk.get("usage")
            
            # We need to envelope with <think> via SSE for streaming compatibility with O1 wrappers
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
                sse_data = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": emit_content}
                    }]
                }
                yield f"data: {json.dumps(sse_data)}\n\n"

            if chunk.get("status") == "finished":
                # Final usage tag optionally included as OpenAI behavior when returning usage on stream
                if final_stream_usage:
                    usage_payload = {
                        "prompt_tokens": final_stream_usage.get("input_tokens", 0),
                        "completion_tokens": final_stream_usage.get("output_tokens", 0),
                        "total_tokens": final_stream_usage.get("total_tokens", 0)
                    }
                    sse_usage = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [],
                        "usage": usage_payload
                    }
                    yield f"data: {json.dumps(sse_usage)}\n\n"
                    
        yield "data: [DONE]\n\n"

    if is_stream:
        return Response(generate_stream(), mimetype='text/event-stream')

    # IF NOT STREAM: consume the entire generator and build the classic JSON
    full_text = ""
    start_think = False
    finish_think = False
    final_usage = {}
    
    for chunk in qwen_session.send_message(messages):
        if "error" in chunk:
            return jsonify({"error": chunk["error"]}), 500
            
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
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.get("model", "qwen"),
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": full_text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": final_usage.get("input_tokens", 0),
            "completion_tokens": final_usage.get("output_tokens", 0),
            "total_tokens": final_usage.get("total_tokens", 0)
        }
    }
    
    return jsonify(response_data)
