import sys
import io
import re
import os

# Force output to utf-8 in Windows terminals (avoids UnicodeEncodeError)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Requires: pip install anthropic
from anthropic import Anthropic

# Test Configurations
STREAM_MODE = True  # Change to False if you want to test Non-Stream mode (waiting for the entire response)
SHOW_TOKENS = True  # Change to False if you do not want to display token usage
SYSTEM_PROMPT = "You are a helpful assistant. Keep your answers concise and direct."

# Initialize the Anthropic client pointing to our Flask port
client = Anthropic(
    api_key="sk-ant-test-chave-ficticia",
    base_url="http://127.0.0.1:5000"
)

def format_terminal_output(text: str):
    """"Formats the Non-Stream mode output by separating <think> from the rest of the text."""
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
    print("=" * 60)
    print("Qwen API Proxy - Continuous Chat Test (Claude Compatible)")
    print(f"Mode: {'[STREAM]' if STREAM_MODE else '[NORMAL]'}")
    print("Type 'exit', 'quit' to terminate.")
    print("=" * 60)
    
    # History managed by the client
    # The Anthropic API handles system prompt separately from the messages array.
    messages = []
    
    while True:
        try:
            user_input = input("\n\033[1mYou:\033[0m ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ["sair", "exit", "quit"]:
                print("\nEnding Claude session. See you soon!")
                break
                
            messages.append({"role": "user", "content": user_input})
            
            if STREAM_MODE:
                print("\033[90m[Connecting to port 5000 SSE...]\033[0m", end="\r")
                sys.stdout.write(" " * 40 + "\r")
                sys.stdout.flush()
                print("\033[92mAssistant:\033[0m ", end="")
                
                full_answer = ""
                in_thought_block = False
                
                input_tokens = 0
                output_tokens = 0

                # Using the official iter stream mode from Anthropic SDK:
                with client.messages.stream(
                    max_tokens=2048,
                    system=SYSTEM_PROMPT,
                    messages=messages,
                    model="qwen3.6-plus"
                ) as stream:
                    for text in stream.text_stream:
                        delta = text or ""
                        full_answer += delta
                        
                        if "<think>" in delta:
                            in_thought_block = True
                            delta = delta.replace("<think>", "")
                            print("\033[90m\n[Thinking:\n", end="")
                            
                        if "</think>" in delta:
                            in_thought_block = False
                            delta = delta.replace("</think>", "")
                            print("]\033[0m\n", end="")
                            
                        if in_thought_block:
                            print(f"\033[90m{delta}\033[0m", end="")
                        else:
                            print(delta, end="")
                        
                        sys.stdout.flush()

                    try:
                        # Extracts token count after the stream finishes
                        final_message = stream.get_final_message()
                        if hasattr(final_message, "usage"):
                            input_tokens = getattr(final_message.usage, "input_tokens", 0)
                            output_tokens = getattr(final_message.usage, "output_tokens", 0)
                    except Exception as e:
                        pass
                        
                print() 
                
                if SHOW_TOKENS:
                    tot_tk = input_tokens + output_tokens
                    print(f"\033[36m[Tokens: Prompt={input_tokens} | Response={output_tokens} | Total={tot_tk}]\033[0m")

                messages.append({"role": "assistant", "content": full_answer})

            else:
                print("\033[33mWaiting for API response in non-stream mode...\033[0m", end="\r")
                response = client.messages.create(
                    max_tokens=2048,
                    model="qwen3.6-plus",
                    system=SYSTEM_PROMPT,
                    messages=messages,
                    stream=False
                )
                
                print(" " * 50, end="\r")
                answer = response.content[0].text
                format_terminal_output(answer)
                
                if SHOW_TOKENS and hasattr(response, "usage"):
                    prompt_tk = getattr(response.usage, "input_tokens", 0)
                    compl_tk = getattr(response.usage, "output_tokens", 0)
                    tot_tk = prompt_tk + compl_tk
                    print(f"\033[36m[Tokens: Prompt={prompt_tk} | Response={compl_tk} | Total={tot_tk}]\033[0m")
                    
                messages.append({"role": "assistant", "content": answer})
            
        except KeyboardInterrupt:
            print("\nSession interrupted by the user.")
            break
        except Exception as e:
            print(f"\n\033[31mError (You may need to run: pip install anthropic)\nException: {e}\033[0m")

if __name__ == "__main__":
    chat_loop()
