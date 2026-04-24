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
        
    tools = req.get("tools", [])
    if tools:
        mapped_tools = []
        for t in tools:
            mapped_tools.append({
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {})
                }
            })
            
        tool_prompt = "You are an AI assistant. You have access to the following tools:\n" + json.dumps(mapped_tools, ensure_ascii=False) + "\n\n"
        tool_prompt += "If you need to use a tool, YOU MUST respond ONLY with the following exact JSON format (and nothing else):\n"
        tool_prompt += "```tool_call\n{\"name\": \"tool_name\", \"arguments\": {\"arg1\": \"value1\"}}\n```\n"
        tool_prompt += "If you do not need to use a tool, just answer normally without the tool_call block."
        system_prompt = system_prompt + "\n\n" + tool_prompt if system_prompt else tool_prompt
        
    print(f"[Claude API] New stateless request received with {len(anthropic_messages)} messages; stream={is_stream}")
    
    # Normalizing Claude-style messages to the format expected by the proxy (OpenAI-like)
    normalized_messages = []
    if system_prompt:
        normalized_messages.append({"role": "system", "content": system_prompt})
        
    for msg in anthropic_messages:
        role = msg.get("role", "user")
        raw_content = msg.get("content", "")
        if isinstance(raw_content, list):
            texts = []
            for block in raw_content:
                if block.get("type", "") == "text":
                    texts.append(block.get("text", ""))
                elif block.get("type", "") == "tool_result":
                    content_val = block.get("content", "")
                    if isinstance(content_val, list):
                        content_val = " ".join([b.get("text", "") for b in content_val if b.get("type") == "text"])
                    texts.append(f"[TOOL RESULT ({block.get('tool_use_id', '')})]\n{content_val}")
                elif block.get("type", "") == "tool_use":
                    texts.append(f"\n[Action Taken]: {json.dumps(block, ensure_ascii=False)}")
            content = "\n\n".join(texts)
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
        answer_buffer = ""
        stop_reason = "end_turn"
        
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
                
                if emit_content:
                    delta_payload = {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": emit_content}}
                    yield f'event: content_block_delta\ndata: {json.dumps(delta_payload)}\n\n'
            else:
                if started_thinking and not finished_thinking:
                    emit_content += "\n</think>\n\n"
                    finished_thinking = True
                    delta_payload = {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": emit_content}}
                    yield f'event: content_block_delta\ndata: {json.dumps(delta_payload)}\n\n'
                
                if tools:
                    answer_buffer += content
                else:
                    emit_content = content
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
                if tools and answer_buffer:
                    if "```tool_call" in answer_buffer:
                        try:
                            pre_text = answer_buffer.split("```tool_call")[0].strip()
                            if pre_text:
                                yield f'event: content_block_delta\ndata: {json.dumps({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": pre_text}})}\n\n'
                                
                            json_str = answer_buffer.split("```tool_call")[1].split("```")[0].strip()
                            tool_call_data = json.loads(json_str)
                            tool_id = f"toolu_{uuid.uuid4().hex[:16]}"
                            
                            yield f'event: content_block_stop\ndata: {{"type": "content_block_stop", "index": 0}}\n\n'
                            
                            start_payload = {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": tool_id, "name": tool_call_data["name"], "input": {}}}
                            yield f'event: content_block_start\ndata: {json.dumps(start_payload)}\n\n'
                            
                            delta_json_payload = {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": json.dumps(tool_call_data.get("arguments", {}))}}
                            yield f'event: content_block_delta\ndata: {json.dumps(delta_json_payload)}\n\n'
                            
                            yield f'event: content_block_stop\ndata: {{"type": "content_block_stop", "index": 1}}\n\n'
                            stop_reason = "tool_use"
                        except Exception as e:
                            print(f"[Claude Tool Call Error] {e}")
                            yield f'event: content_block_delta\ndata: {json.dumps({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": answer_buffer}})}\n\n'
                            yield f'event: content_block_stop\ndata: {{"type": "content_block_stop", "index": 0}}\n\n'
                    else:
                        yield f'event: content_block_delta\ndata: {json.dumps({"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": answer_buffer}})}\n\n'
                        yield f'event: content_block_stop\ndata: {{"type": "content_block_stop", "index": 0}}\n\n'
                else:
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

    stop_reason = "end_turn"
    content_blocks = []
    
    if tools and "```tool_call" in full_text:
        try:
            pre_text = full_text.split("```tool_call")[0].strip()
            if pre_text:
                content_blocks.append({
                    "type": "text",
                    "text": pre_text
                })
                
            json_str = full_text.split("```tool_call")[1].split("```")[0].strip()
            tool_call_data = json.loads(json_str)
            tool_id = f"toolu_{uuid.uuid4().hex[:16]}"
            
            content_blocks.append({
                "type": "tool_use",
                "id": tool_id,
                "name": tool_call_data["name"],
                "input": tool_call_data.get("arguments", {})
            })
            stop_reason = "tool_use"
        except Exception as e:
            content_blocks.append({
                "type": "text",
                "text": full_text
            })
    else:
        content_blocks.append({
            "type": "text",
            "text": full_text
        })

    response_data = {
        "id": f"msg_claude_{uuid.uuid4()}",
        "type": "message",
        "role": "assistant",
        "model": req.get("model", "qwen"),
        "content": content_blocks,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": final_usage.get("input_tokens", 0),
            "output_tokens": final_usage.get("output_tokens", 0)
        }
    }
    
    return jsonify(response_data)
