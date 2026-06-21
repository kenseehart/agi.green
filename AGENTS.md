# Agent onboarding — agi.green (legacy)

## Verdict

**Reference only — do not build new features on this stack.**

| Salvage | Retire for new work |
|---------|---------------------|
| Chat UX patterns | RabbitMQ dependency |
| Python-backend-driven apps idea | Vue 3 + Vite frontend |
| Markdown-in-chat | Docker-first workflow |
| Dispatcher protocol design (as reference) | Vueform |

**Replacement**: `/home/ken/ws/shared/web/chat/` (UI) + FastMCP (tools) + thin Python HTTP handler.

## What this was

Pre-LLM-boom framework (2023–2024) for AI chat apps: WebSocket browser UI, RabbitMQ messaging, OpenAI/Anthropic integration, markdown/forms in chat.

## Repo

- Path: **`/home/ken/ws/agi.green`**
- GitHub: [kenseehart/agi.green](https://github.com/kenseehart/agi.green)
- Related template repo: `agi.green.template` (GitHub template for submodule deploy)

## Key paths (if mining ideas)

| Path | Content |
|------|---------|
| `agi_green/frontend/src/components/Chat.vue` | Original chat UI |
| `agi_green/chat_server.py` | aiohttp + WebSocket server |
| `agi_green/dispatcher.py` | Protocol handler base |
| `agi_green/protocol_*.py` | ws, mq, gpt, http, email protocols |

## Running (legacy)

Requires RabbitMQ + npm build for frontend. Not recommended for new projects.

## Migration checklist

1. Copy chat look-and-feel → `shared/web/chat/`
2. Replace Dispatcher+MQ with direct FastAPI/aiohttp handlers
3. Replace Vue frontend with static HTML + AgiChat
4. Keep domain agi.green for hosting hub / MCP subdomains
