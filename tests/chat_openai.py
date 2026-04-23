import sys
import io
import re

# Force output to utf-8 in Windows terminals (avoids UnicodeEncodeError)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from openai import OpenAI

# Test Configurations
STREAM_MODE = True # Change to False if you want continuous sending mode waiting for the end
SHOW_TOKENS = True  # Change to False if you do not want to display API token usage

# Initialize the client pointing to our API proxy
client = OpenAI(
    api_key="sk-nada-importa-aqui",
    base_url="http://127.0.0.1:5000/v1"
)

def format_terminal_output(text: str):
    """"Formats the Non-Stream mode output to highlight the <think> tag in grey in the terminal"""
    think_pattern = re.compile(r"<think>(.*?)</think>\s*", re.DOTALL)
    
    match = think_pattern.search(text)
    if match:
        thought = match.group(1).strip()
        answer = text[match.end():]
        print(f"\033[90m[Thinking:\n{thought}]\033[0m\n")
        if answer:
            print(f"\033[92mAssistant:\033[0m {answer}")
    else:
        print(f"\033[92mAssistant:\033[0m {text}")

def chat_loop():
    print("=" * 50)
    print("Qwen API Proxy - Continuous Chat Test (OpenAI Compatible)")
    print(f"Mode: {'[STREAM]' if STREAM_MODE else '[NORMAL]'}")
    print("Type 'exit', 'quit' to terminate.")
    print("=" * 50)
    
    # History managed by the client
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Keep your answers concise and direct."}
    ]
    
    while True:
        try:
            user_input = input("\n\033[1mYou:\033[0m ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["sair", "exit", "quit"]:
                print("\nEnding session. See you soon!")
                break
                
            messages.append({"role": "user", "content": user_input})
            
            if STREAM_MODE:
                print("\033[90m[Thinking...]\033[0m", end="\r")
                response = client.chat.completions.create(
                    model="qwen3.6-plus",
                    messages=messages,
                    stream=True,
                    stream_options={"include_usage": True} if SHOW_TOKENS else None
                )
                
                # SSE view control variables
                sys.stdout.write(" " * 40 + "\r")
                sys.stdout.flush()
                
                print("\033[92mAssistant:\033[0m ", end="")
                
                full_answer = ""
                in_thought_block = False
                thought_printed_open = False
                
                usage_data = None
                
                for chunk in response:
                    # Collect usage (comes in the last chunk if stream_options enabled)
                    if getattr(chunk, "usage", None):
                        usage_data = chunk.usage
                        continue
                    
                    if not chunk.choices: # Sometimes the chunk is only for usage
                        continue
                        
                    delta = chunk.choices[0].delta.content or ""
                    full_answer += delta
                    
                    # Simple logic to paint it grey in case it is the thinking block via SSE
                    if "<think>" in delta:
                        in_thought_block = True
                        delta = delta.replace("<think>", "")
                        print("\033[90m\n[Thinking:\n", end="")
                        thought_printed_open = True
                        
                    if "</think>" in delta:
                        in_thought_block = False
                        delta = delta.replace("</think>", "")
                        print("]\033[0m\n", end="")
                        
                    if in_thought_block:
                        print(f"\033[90m{delta}\033[0m", end="")
                    else:
                        print(delta, end="")
                    
                    sys.stdout.flush()
                    
                print() # Line break at the end of the assistant
                
                if SHOW_TOKENS and usage_data:
                    prompt_tk = getattr(usage_data, "prompt_tokens", 0)
                    compl_tk = getattr(usage_data, "completion_tokens", 0)
                    tot_tk = getattr(usage_data, "total_tokens", 0)
                    print(f"\033[36m[Tokens: Prompt={prompt_tk} | Response={compl_tk} | Total={tot_tk}]\033[0m")

                messages.append({"role": "assistant", "content": full_answer})

            else:
                print("\033[33mWaiting for API response...\033[0m", end="\r")
                response = client.chat.completions.create(
                    model="qwen3.6-plus",
                    messages=messages,
                    stream=False
                )
                
                print(" " * 40, end="\r")
                answer = response.choices[0].message.content
                format_terminal_output(answer)
                
                if SHOW_TOKENS and hasattr(response, "usage") and response.usage:
                    prompt_tk = response.usage.prompt_tokens
                    compl_tk = response.usage.completion_tokens
                    tot_tk = response.usage.total_tokens
                    print(f"\033[36m[Tokens: Prompt={prompt_tk} | Response={compl_tk} | Total={tot_tk}]\033[0m")
                    
                messages.append({"role": "assistant", "content": answer})
            
        except KeyboardInterrupt:
            print("\nSession interrupted by the user.")
            break
        except Exception as e:
            print(f"\n\033[31mError during communication: {e}\033[0m")

if __name__ == "__main__":
    chat_loop()
