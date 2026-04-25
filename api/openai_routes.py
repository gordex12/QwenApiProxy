import time
import uuid
import json
from flask import Blueprint, request, jsonify, Response, current_app
from api.usage_routes import track_request

openai_bp = Blueprint('openai', __name__)

@openai_bp.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    req = request.json
    messages = req.get("messages", [])
    is_stream = req.get("stream", False)
    
    if not messages:
        return jsonify({"error": "No messages provided"}), 400
    
    # Normalize messages to handle images and text blocks
    normalized_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        raw_content = msg.get("content", "")
        new_msg = {"role": role, "content": raw_content}
        if "tool_calls" in msg:
            new_msg["tool_calls"] = msg["tool_calls"]
        if "tool_call_id" in msg:
            new_msg["tool_call_id"] = msg["tool_call_id"]
        if "name" in msg:
            new_msg["name"] = msg["name"]
        normalized_messages.append(new_msg)
    
    print(f"[OpenAI API] New stateless request received with {len(normalized_messages)} messages; stream={is_stream}")
    
    tools = req.get("tools", [])
    if tools:
        tool_prompt = "You are an AI assistant. You have access to the following tools:\n" + json.dumps(tools, ensure_ascii=False) + "\n\n"
        tool_prompt += "If you need to use a tool, YOU MUST respond ONLY with the following exact JSON format (and nothing else):\n"
        tool_prompt += "```tool_call\n{\"name\": \"tool_name\", \"arguments\": {\"arg1\": \"value1\"}}\n```\n"
        tool_prompt += "If you do not need to use a tool, just answer normally without the tool_call block."
        
        if normalized_messages and normalized_messages[0].get("role") == "system":
            normalized_messages[0]["content"] += "\n\n" + tool_prompt
        else:
            normalized_messages.insert(0, {"role": "system", "content": tool_prompt})
            
    qwen_session = current_app.config['QWEN_SESSION']
    
    # Count images for usage tracking
    image_count = sum(
        1 for msg in normalized_messages
        if isinstance(msg.get("content"), list)
        for part in (msg.get("content") if isinstance(msg.get("content"), list) else [])
        if part.get("type") == "image_url"
    )

    # Generator that will consume Qwen stream chunks and format them into OpenAI format
    def generate_stream():
        chat_id = f"chatcmpl-{uuid.uuid4()}"
        created = int(time.time())
        model = req.get("model", "qwen")
        
        started_thinking = False
        finished_thinking = False
        final_stream_usage = {}
        answer_buffer = ""

        for chunk in qwen_session.send_message(normalized_messages, model=model):
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
                
                if emit_content:
                    sse_data = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{"index": 0, "delta": {"content": emit_content}}]
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"
            else:
                if started_thinking and not finished_thinking:
                    emit_content += "\n</think>\n\n"
                    finished_thinking = True
                    sse_data = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{"index": 0, "delta": {"content": emit_content}}]
                    }
                    yield f"data: {json.dumps(sse_data)}\n\n"
                
                if tools:
                    answer_buffer += content
                else:
                    emit_content = content
                    if emit_content:
                        sse_data = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model,
                            "choices": [{"index": 0, "delta": {"content": emit_content}}]
                        }
                        yield f"data: {json.dumps(sse_data)}\n\n"

            if chunk.get("status") == "finished":
                if tools and answer_buffer:
                    if "```tool_call" in answer_buffer:
                        try:
                            pre_text = answer_buffer.split("```tool_call")[0].strip()
                            if pre_text:
                                sse_data = {"id": chat_id, "object": "chat.completion.chunk", "created": created, "model": model, "choices": [{"index": 0, "delta": {"content": pre_text}}]}
                                yield f"data: {json.dumps(sse_data)}\n\n"
                                
                            json_str = answer_buffer.split("```tool_call")[1].split("```")[0].strip()
                            tool_call_data = json.loads(json_str)
                            
                            tool_chunk = {
                                "id": chat_id,
                                "object": "chat.completion.chunk",
                                "created": created,
                                "model": model,
                                "choices": [{
                                    "index": 0,
                                    "delta": {
                                        "tool_calls": [{
                                            "index": 0,
                                            "id": f"call_{uuid.uuid4().hex[:8]}",
                                            "type": "function",
                                            "function": {
                                                "name": tool_call_data["name"],
                                                "arguments": json.dumps(tool_call_data.get("arguments", {}), ensure_ascii=False)
                                            }
                                        }]
                                    },
                                    "finish_reason": "tool_calls"
                                }]
                            }
                            yield f"data: {json.dumps(tool_chunk)}\n\n"
                        except Exception as e:
                            print(f"[Tool Call Stream Error] {e}")
                            sse_data = {"id": chat_id, "object": "chat.completion.chunk", "created": created, "model": model, "choices": [{"index": 0, "delta": {"content": answer_buffer}}]}
                            yield f"data: {json.dumps(sse_data)}\n\n"
                    else:
                        sse_data = {"id": chat_id, "object": "chat.completion.chunk", "created": created, "model": model, "choices": [{"index": 0, "delta": {"content": answer_buffer}}]}
                        yield f"data: {json.dumps(sse_data)}\n\n"
                
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

                track_request(
                    "openai",
                    input_tokens=final_stream_usage.get("input_tokens", 0),
                    output_tokens=final_stream_usage.get("output_tokens", 0),
                    images=image_count
                )
                    
        yield "data: [DONE]\n\n"

    if is_stream:
        return Response(generate_stream(), mimetype='text/event-stream')

    # IF NOT STREAM: consume the entire generator and build the classic JSON
    full_text = ""
    start_think = False
    finish_think = False
    final_usage = {}
    
    model = req.get("model", "qwen")
    for chunk in qwen_session.send_message(normalized_messages, model=model):
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

    finish_reason = "stop"
    tool_calls = None
    
    if tools and "```tool_call" in full_text:
        try:
            json_str = full_text.split("```tool_call")[1].split("```")[0].strip()
            tool_call_data = json.loads(json_str)
            tool_calls = [{
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": tool_call_data["name"],
                    "arguments": json.dumps(tool_call_data.get("arguments", {}), ensure_ascii=False)
                }
            }]
            finish_reason = "tool_calls"
            full_text = full_text.split("```tool_call")[0].strip()
        except Exception as e:
            print(f"[Tool Call Error] {e}")

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
            "finish_reason": finish_reason
        }],
        "usage": {
            "prompt_tokens": final_usage.get("input_tokens", 0),
            "completion_tokens": final_usage.get("output_tokens", 0),
            "total_tokens": final_usage.get("total_tokens", 0)
        }
    }

    track_request(
        "openai",
        input_tokens=final_usage.get("input_tokens", 0),
        output_tokens=final_usage.get("output_tokens", 0),
        images=image_count
    )
    
    if tool_calls:
        response_data["choices"][0]["message"]["tool_calls"] = tool_calls
        
    return jsonify(response_data)
