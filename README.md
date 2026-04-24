# Qwen API Proxy

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-blue)

[English](#english) | [Português](#português)

---

## English

**Qwen API Proxy** is an ultra-professional, stateless, local proxy server that enables direct integration with Qwen's Chat platform through OpenAI and Anthropic (Claude) compatible API endpoints.

This project bypasses the need for an official developer API key by seamlessly automating authentication via Selenium (capturing the token directly from your browser session) and maintaining an isolated, stateless conversation history using rich text prompts.

### 🌟 Key Features
- **Dual API Compatibility**: Native support for `/v1/chat/completions` (OpenAI format) and `/v1/messages` (Anthropic format).
- **🖼️ Native Vision / Multimodal Support**: Send images via base64 (OpenAI `image_url` or Claude `image` blocks) and they are automatically uploaded to Alibaba OSS via secure STS tokens, enabling real vision analysis by the Qwen model — no token-heavy Markdown hacks.
- **Auto-Authentication**: If no token is provided, a browser window opens automatically, awaits your manual login, and stealthily captures the session cookie to populate the `.env` file.
- **Thinking Mode Support**: Automatically parses `<think>` tags and maps them to Server-Sent Events (SSE) for seamless compatibility with O1/Claude tools.
- **Function Calling / Tool Use**: Native integration with IDEs and agents via comprehensive tool use support. Intercepts external tool calls, formats system prompts automatically, handles stateless execution logic, and returns results in standard OpenAI/Anthropic format for a seamless AI agent experience.
- **📊 Usage Tracking**: Built-in `/v1/usage` endpoint provides real-time statistics including total requests, token counts, images uploaded, and uptime — perfect for monitoring dashboards.
- **Stateless Architecture**: By compressing context dynamically, it bypasses Qwen's array restrictions while retaining deep context history.
- **Fully Asynchronous Streaming**: Lightning-fast, chunk-by-chunk streaming support for a flicker-free UI experience.
- **Image Optimization**: Automatic resizing (1024px bounding box) and JPEG compression before upload, drastically reducing latency and bandwidth usage. Images smaller than 10px are safely upscaled to prevent backend rejections.
- **Unlimited Free Usage!**

### 🤖 Supported Models
**Important Note:** *Absolutely ALL models available on the official `chat.qwen.ai` platform are supported by this proxy.* 
When sending your API request, you can specify any of the models below in the `model` parameter:
- `qwen3.6-max-preview`
- `qwen3.6-plus`
- `qwen3.6-plus-preview`
- `qwen3.5-plus`
- `qwen3.5-omni-plus`
*(If new models are added to the Qwen website, you can simply pass their exact names in your API calls, and they will work automatically!)*

### 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat endpoint (text + vision) |
| `POST` | `/v1/messages` | Anthropic Claude-compatible chat endpoint (text + vision) |
| `GET`  | `/v1/models` | List available models |
| `GET`  | `/v1/usage` | Real-time proxy usage statistics |

#### Usage Endpoint Response Example
```json
{
  "object": "usage",
  "data": {
    "total_requests": 42,
    "total_input_tokens": 15230,
    "total_output_tokens": 8720,
    "total_tokens": 23950,
    "total_images_uploaded": 3,
    "requests_by_endpoint": {
      "openai": 30,
      "claude": 12
    },
    "uptime_seconds": 3600,
    "started_at": 1776989944
  }
}
```

### 🚀 Getting Started

#### Prerequisites
- Python 3.10 or higher.
- Google Chrome installed.

#### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/gordex12/QwenApiProxy.git
   cd QwenApiProxy
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the Server**:
   ```bash
   python app.py
   ```

#### Standalone Executable
You can also download the pre-built `.exe` from the [Releases](https://github.com/gordex12/QwenApiProxy/releases) page — no Python installation required.

### 🧪 Testing
The `tests/` directory contains testing interfaces for both OpenAI and Claude formats, including vision/image tests.
- `python tests/chat_openai.py` — Interactive OpenAI-format chat
- `python tests/chat_claude.py` — Interactive Claude-format chat
- `pytest tests/test_images.py` — Automated vision/image integration tests

---

## Português

O **Qwen API Proxy** é um servidor proxy local ultra-profissional e "stateless" que permite a integração direta com a plataforma de chat do Qwen através de endpoints compatíveis com a API da OpenAI e da Anthropic (Claude).

Este projeto contorna a necessidade de uma chave de API oficial de desenvolvedor, automatizando a autenticação de forma transparente via Selenium (capturando o token diretamente da sua sessão de navegador) e mantendo um histórico de conversa isolado e "stateless" usando prompts de texto enriquecido.

### 🌟 Principais Recursos
- **Compatibilidade Dupla de API**: Suporte nativo para `/v1/chat/completions` (formato OpenAI) e `/v1/messages` (formato Anthropic).
- **🖼️ Suporte Nativo a Visão / Multimodal**: Envie imagens via base64 (blocos `image_url` do OpenAI ou `image` do Claude) e elas são automaticamente enviadas para o Alibaba OSS via tokens STS seguros, habilitando a análise visual real pelo modelo Qwen — sem hacks de Markdown que consomem tokens.
- **Autenticação Automática**: Se nenhum token for fornecido, uma janela do navegador é aberta automaticamente, aguarda seu login manual e captura silenciosamente o cookie da sessão para preencher o arquivo `.env`.
- **Suporte ao Modo "Pensamento"**: Faz a análise (parse) automática das tags `<think>` e as mapeia para Server-Sent Events (SSE) para compatibilidade perfeita com ferramentas do padrão O1/Claude.
- **Function Calling / Tool Use**: Integração nativa com IDEs e agentes via suporte completo ao uso de ferramentas. Intercepta requisições de tools, formata automaticamente system prompts dinâmicos, lida com lógica de execução stateless e retorna o uso das ferramentas seguindo estritamente os padrões e respostas da OpenAI/Anthropic.
- **📊 Rastreamento de Uso**: Endpoint `/v1/usage` embutido com estatísticas em tempo real incluindo total de requisições, contagem de tokens, imagens enviadas e tempo online — perfeito para dashboards de monitoramento.
- **Arquitetura Stateless**: Ao comprimir o contexto dinamicamente, ele contorna as restrições de array do Qwen enquanto mantém um profundo histórico de contexto.
- **Streaming Totalmente Assíncrono**: Suporte a streaming extremamente rápido (chunk-by-chunk) para uma experiência de UI contínua e sem travamentos.
- **Otimização de Imagem**: Redimensionamento automático (bounding box de 1024px) e compressão JPEG antes do upload, reduzindo drasticamente a latência e uso de banda. Imagens menores que 10px são ampliadas com segurança para evitar rejeições do backend.
- **Uso Gratuito e Sem Limites!**

### 🤖 Modelos Suportados
**Observação Importante:** *Absolutamente TODOS os modelos disponíveis na plataforma oficial `chat.qwen.ai` funcionam e são suportados por este proxy.*
Ao enviar a requisição para a API, você pode especificar qualquer um dos modelos abaixo no parâmetro `model`:
- `qwen3.6-max-preview`
- `qwen3.6-plus`
- `qwen3.6-plus-preview`
- `qwen3.5-plus`
- `qwen3.5-omni-plus`
*(Se novos modelos forem adicionados ao site do Qwen, basta passar o nome exato deles na sua chamada de API e eles funcionarão automaticamente!)*

### 📡 Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/v1/chat/completions` | Endpoint de chat compatível com OpenAI (texto + visão) |
| `POST` | `/v1/messages` | Endpoint de chat compatível com Anthropic Claude (texto + visão) |
| `GET`  | `/v1/models` | Listar modelos disponíveis |
| `GET`  | `/v1/usage` | Estatísticas de uso do proxy em tempo real |

### 🚀 Começando

#### Pré-requisitos
- Python 3.10 ou superior.
- Google Chrome instalado.

#### Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/gordex12/QwenApiProxy.git
   cd QwenApiProxy
   ```

2. Instale as dependências necessárias:
   ```bash
   pip install -r requirements.txt
   ```

3. **Inicie o Servidor**:
   ```bash
   python app.py
   ```

#### Executável Standalone
Você também pode baixar o `.exe` pré-compilado na página de [Releases](https://github.com/gordex12/QwenApiProxy/releases) — sem necessidade de instalar Python.

### 🧪 Testes
O diretório `tests/` contém interfaces de teste para os formatos OpenAI e Claude, incluindo testes de visão/imagem.
- `python tests/chat_openai.py` — Chat interativo no formato OpenAI
- `python tests/chat_claude.py` — Chat interativo no formato Claude
- `pytest tests/test_images.py` — Testes automatizados de integração de visão/imagem

---

## 📜 License / Licença
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
Este projeto é licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.
