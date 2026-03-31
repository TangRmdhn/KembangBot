---
title: Kembang AI Service
emoji: 🌸
colorFrom: purple
colorTo: teal
sdk: docker
pinned: false
app_port: 7860
---

# Kembang AI Backend

🤖 **AI Sales Agent Platform for Indonesian SMEs** — WhatsApp-integrated conversational AI that helps businesses automate customer conversations, collect leads, and close sales.

## Quick Start

### Local Development

```bash
# Copy environment file
cp .env.example .env

# Edit .env with your credentials
# - OPENAI_API_KEY
# - APP_SECRET_KEY
# - etc.

# Run with Docker
docker compose up --build

# Access Swagger UI
open http://localhost:7860/docs
```

### Deploy to Hugging Face Spaces

1. **Setup Neon Database**
   - Go to https://neon.tech → Create project
   - Copy async + sync connection strings

2. **Setup Upstash Redis**
   - Go to https://upstash.com → Create database
   - Copy Redis URL (rediss:// format)

3. **Create HF Space**
   - Go to https://huggingface.co/spaces → Create new Space
   - SDK: Docker
   - Push this code to the Space repo

4. **Set Secrets in HF Spaces Settings**
   - `APP_SECRET_KEY`
   - `DATABASE_URL` (Neon async)
   - `DATABASE_URL_SYNC` (Neon sync)
   - `REDIS_URL` (Upstash)
   - `OPENAI_API_KEY`
   - `WAHA_BASE_URL`
   - `WAHA_WEBHOOK_SECRET`
   - `INTERNAL_API_KEY`

5. **Run Migrations**
   ```bash
   # Locally with Neon credentials
   alembic upgrade head
   ```

6. **Seed Demo Data (optional)**
   ```bash
   python -m app.services.seeder
   ```

## Features

- ✅ Multi-tenant WhatsApp AI agent
- ✅ Configurable conversation flows
- ✅ Product catalog with semantic search (RAG)
- ✅ Document knowledge base (FAQ, policies)
- ✅ Lead management
- ✅ Stage-based conversation routing
- ✅ LangGraph + OpenAI integration

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + pgvector (Neon)
- **Cache**: Redis (Upstash)
- **AI**: LangGraph, LangChain, OpenAI GPT-4o-mini
- **WhatsApp**: WAHA integration

## API Documentation

After deployment, access Swagger UI at:
```
https://YOUR_USERNAME-kembang-ai-service.hf.space/docs
```

## Environment Variables

See `.env.example` for all required variables.

## License

MIT
