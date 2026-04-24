import json
import time
import sys
import io

# Force utf-8 encoding for Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from openai import OpenAI

client = OpenAI(
    api_key="sk-nada-importa-aqui",
    base_url="http://127.0.0.1:5000/v1"
)

WEATHER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Obtém a previsão do tempo para uma cidade",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "A cidade e estado, ex: São Paulo, SP"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"]
                    }
                },
                "required": ["location"]
            }
        }
    }
]

def test_scenario(name, messages, tools=None, stream=False, expect_tool=False):
    print(f"\n{'='*50}\n> OPENAI TEST: {name} (Stream: {stream})\n{'='*50}")
    
    start_time = time.time()
    try:
        kwargs = {
            "model": "qwen3.6-plus",
            "messages": messages,
            "stream": stream
        }
        if tools:
            kwargs["tools"] = tools
            
        response = client.chat.completions.create(**kwargs)
        
        tool_calls = []
        final_content = ""
        
        if stream:
            print("Recebendo stream...")
            for chunk in response:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tool_calls.append({
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        })
                elif delta.content:
                    final_content += delta.content
                    print(delta.content, end="", flush=True)
            print()
            if tool_calls:
                print("\n[STREAM] Tool Call Recebido:", json.dumps(tool_calls, indent=2, ensure_ascii=False))
        else:
            message = response.choices[0].message
            final_content = message.content or ""
            
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
                print("\n[NON-STREAM] Tool Call Recebido:")
                print(json.dumps(tool_calls, indent=2, ensure_ascii=False))
            else:
                print("\n[NON-STREAM] Resposta:")
                print(final_content)
                
        if expect_tool and not tool_calls:
            print("❌ FALHA: Era esperado uma chamada de ferramenta, mas nenhuma foi recebida.")
        elif not expect_tool and tool_calls:
            print("❌ FALHA: NÃO era esperado uma chamada de ferramenta, mas o modelo tentou chamar uma.")
        else:
            print("✅ SUCESSO: O comportamento da ferramenta ocorreu conforme esperado.")
            
        print(f"⏱ Tempo decorrido: {time.time() - start_time:.2f}s")
        return final_content, tool_calls
        
    except Exception as e:
        print(f"❌ ERRO na requisição: {e}")
        return None, None

def run_all_tests():
    print("Iniciando bateria de testes da OpenAI API (usando SDK oficial)...")
    
    messages = [
        {"role": "system", "content": "Você é um assistente prestativo. Use as ferramentas fornecidas quando necessário."},
        {"role": "user", "content": "Qual é a previsão do tempo em Nova York?"}
    ]
    test_scenario("Tool Call Básico (Non-Stream)", messages, WEATHER_TOOLS, stream=False, expect_tool=True)
    test_scenario("Tool Call Básico (Stream)", messages, WEATHER_TOOLS, stream=True, expect_tool=True)
    
    messages_multi = [
        {"role": "system", "content": "Você é um assistente prestativo."},
        {"role": "user", "content": "Qual a previsão do tempo no Rio de Janeiro?"}
    ]
    _, tool_calls = test_scenario("Multi-Turn - Fase 1", messages_multi, WEATHER_TOOLS, stream=True, expect_tool=True)
    
    if tool_calls:
        messages_multi.append({
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls
        })
        messages_multi.append({
            "role": "tool",
            "tool_call_id": tool_calls[0]["id"],
            "name": tool_calls[0]["function"]["name"],
            "content": "{\"temperature\": 32, \"condition\": \"Ensolarado e muito quente\"}"
        })
        test_scenario("Multi-Turn - Fase 2", messages_multi, WEATHER_TOOLS, stream=True, expect_tool=False)

if __name__ == "__main__":
    run_all_tests()
