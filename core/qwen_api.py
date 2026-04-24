import time
import uuid
import json
import requests

class SimpleQwenAPI:
    BASE_URL = "https://chat.qwen.ai"

    def __init__(self, token: str):
        self.token = token
        self.model = "qwen3.6-plus"
        self.chat_id = None
        self.parent_id = None

    def get_headers(self):
        """Return the headers required for Qwen API requests."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json, text/plain, */*',
            'Authorization': f'Bearer {self.token}',
            'Origin': self.BASE_URL,
            'Referer': f'{self.BASE_URL}/',
            'version': '0.2.40'
        }

    def init_chat(self) -> str:
        url = f"{self.BASE_URL}/api/v2/chats/new"
        payload = {
            "models": [self.model],
            "chat_mode": "local",
            "chat_type": "t2t",
            "timestamp": int(time.time() * 1000),
            "project_id": "",
            "title": "API Stateless Chat"
        }
        res = requests.post(url, json=payload, headers=self.get_headers())
        data = res.json()
        if res.status_code == 200 and data.get("success"):
            return data["data"]["id"]
        return None

    def send_message(self, messages_array: list):
        """Send a message to the Qwen API and yield the stream chunks."""
        chat_id = self.init_chat()
        if not chat_id:
            yield {"error": "Error initializing Qwen session"}
            return

        url = f"{self.BASE_URL}/api/v2/chat/completions?chat_id={chat_id}"
        timestamp = int(time.time() * 1000)

        qwen_messages = []
        
        # Since the Qwen web backend blocks arrays containing multiple messages
        # and we operate in a 100% stateless manner (creating new chats on every request),
        # we need to compact the history and convert it into a single rich text prompt.
        full_context_prompt = ""
        for open_msg in messages_array:
            role = open_msg.get("role", "user")
            content = open_msg.get("content", "")
            
            if role == "assistant" and "<think>" in content:
                content = content.split("</think>")[-1].strip()
                
            if role == "system":
                full_context_prompt += f"[SYSTEM]\n{content}\n\n"
            elif role == "assistant":
                tool_calls = open_msg.get("tool_calls", [])
                if tool_calls:
                    content += "\n[Action Taken]: " + json.dumps(tool_calls, ensure_ascii=False)
                full_context_prompt += f"[ASSISTANT]\n{content}\n\n"
            elif role in ["tool", "function"]:
                tool_id = open_msg.get("tool_call_id", "")
                full_context_prompt += f"[TOOL RESULT ({tool_id})]\n{content}\n\n"
            else:
                full_context_prompt += f"[USER]\n{content}\n\n"

        full_context_prompt += "[ASSISTANT]\n"

        msg_id = str(uuid.uuid4())
        qwen_msg = {
            "fid": msg_id,
            "childrenIds": [],
            "role": "user",
            "content": full_context_prompt.strip(),
            "timestamp": timestamp,
            "feature_config": {
                "thinking_enabled": True, 
                "output_schema": "phase", 
                "research_mode": "normal", 
                "auto_thinking": False, 
                "thinking_mode": "Thinking", 
                "auto_search": False
            },
            "extra": {"meta": {"subChatType": "t2t"}},
            "sub_chat_type": "t2t",
            "parent_id": None,
            "parentId": None,
            "user_action": "chat",
            "files": [],
            "models": [self.model],
            "chat_type": "t2t"
        }
        
        qwen_messages.append(qwen_msg)

        payload = {
            "stream": True,
            "version": "2.1",
            "incremental_output": True,
            "chat_id": chat_id,
            "chat_mode": "local",
            "model": self.model,
            "messages": qwen_messages,
            "timestamp": timestamp,
            "parent_id": None,
            "parentId": None
        }

        res = requests.post(url, json=payload, headers=self.get_headers(), stream=True)
        if res.status_code != 200:
            yield {"error": f"Status {res.status_code}: {res.text}"}
            return

        # Read the stream blocks and forward events
        for line in res.iter_lines():
            if not line: continue
            line_str = line.decode('utf-8').strip()
            if line_str.startswith('data:'):
                data_str = line_str[5:].strip()
                if data_str == '[DONE]': break
                try:
                    chunk = json.loads(data_str)
                    
                    if "error" in chunk:
                        yield {"error": f"Qwen API Error: {chunk['error']}"}
                        break
                    
                    usage = chunk.get("usage", {})
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    phase = delta.get("phase")
                    content = delta.get("content", "")
                    status = delta.get("status")

                    is_thinking = False
                    # Capture thinking process
                    if phase in ["think", "thinking", "thinking_summary"]:
                        thinking_extras = delta.get("extra", {})
                        thought_list = thinking_extras.get("summary_thought", {}).get("content", [])
                        if thought_list:
                            content = " ".join(thought_list) + "\n"
                            is_thinking = True
                        elif content:
                            is_thinking = True
                    
                    elif phase == "answer" or not phase:
                        is_thinking = False
                        
                    yield {
                        "content": content,
                        "is_thinking": is_thinking,
                        "status": status,
                        "usage": usage
                    }

                    if status == "finished" and phase == "answer":
                        break
                except Exception as e:
                    print(f"[API ERROR] {e} in chunk: {data_str}")
                    continue
