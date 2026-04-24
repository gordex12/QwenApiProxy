import json
import time
import sys
import io

# Force utf-8 encoding for Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from anthropic import Anthropic

client = Anthropic(
    api_key="sk-nada-importa-aqui",
    base_url="http://127.0.0.1:5000"  # Anthropic SDK automatically appends /v1/messages
)

CLAUDE_TOOLS = [
    {
        "name": "get_weather",
        "description": "Obtém a previsão do tempo para uma cidade",
        "input_schema": {
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
]

def test_scenario(name, messages, system_prompt="", tools=None, stream=False, expect_tool=False):
    print(f"\n{'='*50}\n> CLAUDE TEST: {name} (Stream: {stream})\n{'='*50}")
    
    start_time = time.time()
    try:
        kwargs = {
            "model": "qwen3.6-plus",
            "messages": messages,
            "max_tokens": 4096
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = tools
            
        tool_uses = []
        final_content = ""
        
        if stream:
            print("Recebendo stream...")
            with client.messages.stream(**kwargs) as response_stream:
                for event in response_stream:
                    if event.type == "text":
                        final_content += event.text
                        print(event.text, end="", flush=True)
            print()
            
            # The Anthropic stream SDK automatically parses the tools for us!
            message = response_stream.get_final_message()
            for block in message.content:
                if block.type == "tool_use":
                    tool_uses.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
            
            if tool_uses:
                print("\n[STREAM] Tool Use Recebido:", json.dumps(tool_uses, indent=2, ensure_ascii=False))
        else:
            response = client.messages.create(**kwargs)
            for block in response.content:
                if block.type == "text":
                    final_content += block.text
                elif block.type == "tool_use":
                    tool_uses.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
            
            if tool_uses:
                print("\n[NON-STREAM] Tool Use Recebido:")
                print(json.dumps(tool_uses, indent=2, ensure_ascii=False))
            if final_content:
                print("\n[NON-STREAM] Resposta de texto:")
                print(final_content)
                
        if expect_tool and not tool_uses:
            print("❌ FALHA: Era esperado uma chamada de ferramenta, mas nenhuma foi recebida.")
        elif not expect_tool and tool_uses:
            print("❌ FALHA: NÃO era esperado uma chamada de ferramenta, mas o modelo tentou chamar uma.")
        else:
            print("✅ SUCESSO: O comportamento da ferramenta ocorreu conforme esperado.")
            
        print(f"⏱ Tempo decorrido: {time.time() - start_time:.2f}s")
        return final_content, tool_uses
        
    except Exception as e:
        print(f"❌ ERRO na requisição: {e}")
        return None, None

def run_all_tests():
    print("Iniciando bateria de testes da CLAUDE API (usando SDK oficial)...")
    
    system_prompt = "Você é um assistente prestativo. Use as ferramentas fornecidas quando necessário."
    
    messages = [
        {"role": "user", "content": "Qual é a previsão do tempo em Paris?"}
    ]
    test_scenario("Tool Use Básico (Non-Stream)", messages, system_prompt, CLAUDE_TOOLS, stream=False, expect_tool=True)
    test_scenario("Tool Use Básico (Stream)", messages, system_prompt, CLAUDE_TOOLS, stream=True, expect_tool=True)
    
    messages_multi = [
        {"role": "user", "content": "Qual a previsão do tempo no Rio de Janeiro?"}
    ]
    _, tool_uses = test_scenario("Multi-Turn - Fase 1", messages_multi, system_prompt, CLAUDE_TOOLS, stream=True, expect_tool=True)
    
    if tool_uses:
        messages_multi.append({
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_uses[0]["id"],
                    "name": tool_uses[0]["name"],
                    "input": tool_uses[0].get("input", {})
                }
            ]
        })
        messages_multi.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_uses[0]["id"],
                    "content": "{\"temperature\": 32, \"condition\": \"Ensolarado e muito quente\"}"
                }
            ]
        })
        test_scenario("Multi-Turn - Fase 2", messages_multi, system_prompt, CLAUDE_TOOLS, stream=True, expect_tool=False)

if __name__ == "__main__":
    run_all_tests()
