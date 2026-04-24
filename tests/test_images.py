import sys
import io

# Force utf-8 encoding for Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from openai import OpenAI
from anthropic import Anthropic

# Tiny 5x5 red dot PNG base64
RED_DOT_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="

def test_openai_image():
    print("=" * 50)
    print("Testing OpenAI Image Support")
    print("=" * 50)
    
    client = OpenAI(
        api_key="sk-nada-importa-aqui",
        base_url="http://127.0.0.1:5000/v1"
    )
    
    response = client.chat.completions.create(
        model="qwen3.6-plus",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "O que você vê nesta imagem? Responda em apenas 1 frase."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{RED_DOT_B64}"
                        }
                    }
                ]
            }
        ],
        stream=False
    )
    
    print("Response:")
    print(response.choices[0].message.content)
    print("\n✅ OpenAI Image Test Finished\n")

def test_claude_image():
    print("=" * 50)
    print("Testing Claude Image Support")
    print("=" * 50)
    
    client = Anthropic(
        api_key="sk-nada-importa-aqui",
        base_url="http://127.0.0.1:5000"
    )
    
    response = client.messages.create(
        model="qwen3.6-plus",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "O que você vê nesta imagem? Responda em apenas 1 frase."},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": RED_DOT_B64
                        }
                    }
                ]
            }
        ]
    )
    
    print("Response:")
    for block in response.content:
        if block.type == "text":
            print(block.text)
            
    print("\n✅ Claude Image Test Finished\n")

if __name__ == "__main__":
    test_openai_image()
    test_claude_image()
