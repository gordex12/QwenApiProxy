import time
import uuid
import json
import hashlib
import requests
import os

class SimpleQwenAPI:
    BASE_URL = "https://chat.qwen.ai"

    def __init__(self, token: str):
        self.token = token
        self.model = os.getenv("QWEN_MODEL", "qwen3.6-plus")
        self.chat_id = None
        self.parent_id = None
        self._image_cache = {}  # SHA-256 -> file_obj cache to avoid re-uploads

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

    def upload_image_to_oss(self, base64_str: str) -> dict:
        import base64
        import uuid
        import oss2
        from .image_utils import optimize_base64_image

        try:
            if not base64_str.startswith("data:"):
                base64_str = f"data:image/jpeg;base64,{base64_str}"
            
            # The optimization ensures the image fits constraints (not too big, but > 10x10)
            optimized_b64 = optimize_base64_image(base64_str)
            raw_b64 = optimized_b64.split(",", 1)[-1]

            # Check cache by content hash to avoid re-uploading the same image
            content_hash = hashlib.sha256(raw_b64.encode("utf-8")).hexdigest()
            if content_hash in self._image_cache:
                print(f"[QwenAPI] Image cache hit ({content_hash[:12]}...), skipping upload")
                return self._image_cache[content_hash]

            image_data = base64.b64decode(raw_b64)
            filesize = len(image_data)

            sts_payload = {
                'filename': 'image.jpg',
                'filesize': filesize,
                'filetype': 'image'
            }
            sts_res = requests.post(f'{self.BASE_URL}/api/v2/files/getstsToken', json=sts_payload, headers=self.get_headers())
            sts_data = sts_res.json().get('data', {})

            if not sts_data:
                print("[OSS Upload] Failed to get STS token")
                return None

            access_key_id = sts_data['access_key_id']
            access_key_secret = sts_data['access_key_secret']
            security_token = sts_data['security_token']
            endpoint = sts_data['endpoint']
            bucket_name = sts_data['bucketname']
            file_path = sts_data['file_path']
            file_id = sts_data['file_id']
            file_url = sts_data['file_url']

            auth = oss2.StsAuth(access_key_id, access_key_secret, security_token)
            bucket = oss2.Bucket(auth, endpoint, bucket_name)
            bucket.put_object(file_path, image_data, headers={'Content-Type': 'image/jpeg'})
            
            timestamp = int(time.time() * 1000)
            user_id = file_path.split('/')[0]

            result = {
                "type": "image",
                "file": {
                    "created_at": timestamp,
                    "data": {},
                    "filename": "image.jpg",
                    "hash": None,
                    "id": file_id,
                    "user_id": user_id,
                    "meta": {
                        "name": "image.jpg",
                        "size": filesize,
                        "content_type": "image/jpeg"
                    },
                    "update_at": timestamp
                },
                "id": file_id,
                "url": file_url,
                "name": "image.jpg",
                "collection_name": "",
                "progress": 0,
                "status": "uploaded",
                "greenNet": "success",
                "size": filesize,
                "error": "",
                "itemId": str(uuid.uuid4()),
                "file_type": "image/jpeg",
                "showType": "image",
                "file_class": "vision",
                "uploadTaskId": str(uuid.uuid4())
            }

            # Cache the result so the same image won't be re-uploaded
            self._image_cache[content_hash] = result
            print(f"[QwenAPI] Image cached ({content_hash[:12]}...)")
            return result
        except Exception as e:
            print(f"[OSS Upload] Error uploading image: {e}")
            return None

    def send_message(self, messages_array: list, model: str = None):
        """Send a message to the Qwen API and yield the stream chunks."""
        chat_id = self.init_chat()
        if not chat_id:
            yield {"error": "Error initializing Qwen session"}
            return

        # Use the requested model if it starts with 'qwen', otherwise fallback to default
        current_model = self.model
        if model and model.lower().startswith("qwen"):
            current_model = model

        url = f"{self.BASE_URL}/api/v2/chat/completions?chat_id={chat_id}"
        timestamp = int(time.time() * 1000)

        qwen_messages = []
        qwen_files = []
        
        system_blocks = []
        history_blocks = []
        
        for open_msg in messages_array:
            role = open_msg.get("role", "user")
            raw_content = open_msg.get("content", "")
            content_str = ""
            
            if isinstance(raw_content, list):
                text_parts = []
                for part in raw_content:
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        image_url = part.get("image_url", {}).get("url", "")
                        if image_url.startswith("data:image"):
                            print("[QwenAPI] Found base64 image, uploading to OSS...")
                            file_obj = self.upload_image_to_oss(image_url)
                            if file_obj:
                                qwen_files.append(file_obj)
                        else:
                            text_parts.append(f"![image]({image_url})")
                content_str = "\n".join(text_parts)
            else:
                content_str = raw_content
                
            if role == "assistant" and "<think>" in content_str:
                content_str = content_str.replace("<think>", "<past_reasoning>").replace("</think>", "</past_reasoning>")
                
            if role == "system":
                system_blocks.append(f"<system_directives>\n{content_str.strip()}\n</system_directives>")
            elif role == "assistant":
                tool_calls = open_msg.get("tool_calls", [])
                if tool_calls:
                    tool_calls_str = ""
                    for tc in tool_calls:
                        tc_id = tc.get("id", "")
                        fn_name = tc.get("function", {}).get("name", "")
                        fn_args = tc.get("function", {}).get("arguments", "{}")
                        if not isinstance(fn_args, str):
                            fn_args = json.dumps(fn_args, ensure_ascii=False)
                        tool_calls_str += f'<tool_call id="{tc_id}" name="{fn_name}">\n{fn_args}\n</tool_call>\n'
                    content_str += f"\n<assistant_action>\n{tool_calls_str.strip()}\n</assistant_action>"
                history_blocks.append(f"<assistant>\n{content_str.strip()}\n</assistant>")
            elif role in ["tool", "function"]:
                tool_id = open_msg.get("tool_call_id", "")
                history_blocks.append(f'<tool_result id="{tool_id}">\n{content_str.strip()}\n</tool_result>')
            else:
                history_blocks.append(f"<user>\n{content_str.strip()}\n</user>")

        full_context_prompt = "\n\n".join(system_blocks) + "\n\n"
        
        if len(history_blocks) > 1:
            full_context_prompt += "<execution_history>\n"
            full_context_prompt += "\n\n".join(history_blocks[:-1])
            full_context_prompt += "\n</execution_history>\n\n"
            full_context_prompt += f"<current_task>\n{history_blocks[-1]}\n</current_task>"
        elif len(history_blocks) == 1:
            full_context_prompt += f"<current_task>\n{history_blocks[0]}\n</current_task>"

        full_context_prompt += "\n\n<system_reminder>Crucial: You must think, reason, and write your final response in the EXACT same language that the user is speaking in the <current_task>.</system_reminder>"

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
            "files": qwen_files,
            "models": [current_model],
            "chat_type": "t2t"
        }
        
        qwen_messages.append(qwen_msg)

        payload = {
            "stream": True,
            "version": "2.1",
            "incremental_output": True,
            "chat_id": chat_id,
            "chat_mode": "local",
            "model": current_model,
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
