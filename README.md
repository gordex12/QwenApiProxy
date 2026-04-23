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
- **Auto-Authentication**: If no token is provided, a browser window opens automatically, awaits your manual login, and stealthily captures the session cookie to populate the `.env` file.
- **Thinking Mode Support**: Automatically parses `<think>` tags and maps them to Server-Sent Events (SSE) for seamless compatibility with O1/Claude tools.
- **Stateless Architecture**: By compressing context dynamically, it bypasses Qwen's array restrictions while retaining deep context history.
- **Fully Asynchronous Streaming**: Lightning-fast, chunk-by-chunk streaming support for a flicker-free UI experience.

### 🤖 Supported Models
**Important Note:** *Absolutely ALL models available on the official `chat.qwen.ai` platform are supported by this proxy.* 
When sending your API request, you can specify any of the models below in the `model` parameter:
- `qwen3.6-max-preview`
- `qwen3.6-plus`
- `qwen3.6-plus-preview`
- `qwen3.5-plus`
- `qwen3.5-omni-plus`
*(If new models are added to the Qwen website, you can simply pass their exact names in your API calls, and they will work automatically!)*

### 🚀 Getting Started

#### Prerequisites
- Python 3.10 or higher.
- Google Chrome installed.

#### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/QwenApiProxy.git
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

### 🧪 Testing
The `tests/` directory contains generic Chat testing interfaces for both OpenAI and Claude formats.
- `python tests/chat_openai.py`
- `python tests/chat_claude.py`

---

## Português

O **Qwen API Proxy** é um servidor proxy local ultra-profissional e "stateless" que permite a integração direta com a plataforma de chat do Qwen através de endpoints compatíveis com a API da OpenAI e da Anthropic (Claude).

Este projeto contorna a necessidade de uma chave de API oficial de desenvolvedor, automatizando a autenticação de forma transparente via Selenium (capturando o token diretamente da sua sessão de navegador) e mantendo um histórico de conversa isolado e "stateless" usando prompts de texto enriquecido.

### 🌟 Principais Recursos
- **Compatibilidade Dupla de API**: Suporte nativo para `/v1/chat/completions` (formato OpenAI) e `/v1/messages` (formato Anthropic).
- **Autenticação Automática**: Se nenhum token for fornecido, uma janela do navegador é aberta automaticamente, aguarda seu login manual e captura silenciosamente o cookie da sessão para preencher o arquivo `.env`.
- **Suporte ao Modo "Pensamento"**: Faz a análise (parse) automática das tags `<think>` e as mapeia para Server-Sent Events (SSE) para compatibilidade perfeita com ferramentas do padrão O1/Claude.
- **Arquitetura Stateless**: Ao comprimir o contexto dinamicamente, ele contorna as restrições de array do Qwen enquanto mantém um profundo histórico de contexto.
- **Streaming Totalmente Assíncrono**: Suporte a streaming extremamente rápido (chunk-by-chunk) para uma experiência de UI contínua e sem travamentos.

### 🤖 Modelos Suportados
**Observação Importante:** *Absolutamente TODOS os modelos disponíveis na plataforma oficial `chat.qwen.ai` funcionam e são suportados por este proxy.*
Ao enviar a requisição para a API, você pode especificar qualquer um dos modelos abaixo no parâmetro `model`:
- `qwen3.6-max-preview`
- `qwen3.6-plus`
- `qwen3.6-plus-preview`
- `qwen3.5-plus`
- `qwen3.5-omni-plus`
*(Se novos modelos forem adicionados ao site do Qwen, basta passar o nome exato deles na sua chamada de API e eles funcionarão automaticamente!)*

### 🚀 Começando

#### Pré-requisitos
- Python 3.10 ou superior.
- Google Chrome instalado.

#### Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/your-username/QwenApiProxy.git
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

### 🧪 Testes
O diretório `tests/` contém interfaces genéricas de teste de Chat para os formatos OpenAI e Claude.
- `python tests/chat_openai.py`
- `python tests/chat_claude.py`

---

## 📜 License / Licença
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
Este projeto é licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.
