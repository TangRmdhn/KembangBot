# Kembang AI Backend

🤖 **AI Sales Agent Platform for Indonesian SMEs** — WhatsApp-integrated conversational AI that helps businesses automate customer conversations, collect leads, and close sales.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Demo Data](#demo-data)

---

## 🎯 Overview

Kembang AI is a B2B SaaS platform that provides AI-powered sales agents for Indonesian SMEs. The system integrates with WhatsApp via WAHA (WhatsApp HTTP API) and uses LangGraph to create intelligent, stage-based conversation flows.

**Key Capabilities:**
- 🧠 Configurable conversation flows with custom stages
- 📦 Product/service catalog with semantic search (RAG)
- 💬 Natural Bahasa Indonesia conversations
- 📊 Lead management and tracking
- 🔌 WAHA webhook integration for WhatsApp
- 🏢 Multi-tenant architecture with complete data isolation

---

## ✨ Features

### Layer 1: Backend Foundation
- ✅ FastAPI with async SQLAlchemy + PostgreSQL
- ✅ Redis caching for sessions and stage configs
- ✅ WAHA webhook handler with HMAC verification
- ✅ Multi-tenant data isolation
- ✅ JWT/API key authentication
- ✅ Docker + docker-compose setup

### Layer 2: LangGraph Engine
- ✅ **Supervisor Node**: Intent classification + field extraction
- ✅ **Conversation Agent**: Natural responses with tool execution
- ✅ **Formatter**: WhatsApp-optimized response formatting
- ✅ **Tools**: `search_catalog`, `check_pricing_rules`, `save_lead_info`
- ✅ Stage-based conversation routing

### Layer 3: RAG + Stage Config
- ✅ **pgvector** semantic search for product catalogs
- ✅ CSV catalog upload with automatic embedding
- ✅ Stage flow builder API (create/edit/reorder)
- ✅ Flow validation before deployment
- ✅ Demo seeder with photography + sneaker shop flows

---

## 🛠 Tech Stack

| Category | Technology |
|----------|-----------|
| **Framework** | FastAPI, Uvicorn |
| **Database** | PostgreSQL 16 + pgvector |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Cache** | Redis 7 |
| **AI/LLM** | LangGraph, LangChain, OpenAI GPT-4o-mini |
| **Embeddings** | OpenAI text-embedding-3-small |
| **Vector Store** | langchain-postgres (PGVector) |
| **WhatsApp** | WAHA (WhatsApp HTTP API) |
| **Migrations** | Alembic |
| **Container** | Docker, docker-compose |
| **Testing** | pytest, pytest-asyncio |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      WhatsApp Users                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                         WAHA Server                         │
│              (WhatsApp HTTP API Gateway)                    │
└────────────────────────┬────────────────────────────────────┘
                         │ Webhook (HMAC signed)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Kembang AI Backend                        │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Webhook   │  │  LangGraph   │  │   Dashboard     │   │
│  │   Handler   │─▶│   Engine     │  │   API           │   │
│  └─────────────┘  └──────────────┘  └─────────────────┘   │
│         │                │                      │           │
│         ▼                ▼                      ▼           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Service Layer                          │   │
│  │  Tenant | Conversation | Stage | Lead | Catalog    │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                │                      │           │
│         ▼                ▼                      ▼           │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  PostgreSQL  │  │    Redis     │  │   pgvector      │  │
│  │  (Tenant,    │  │  (Cache,     │  │   (Embeddings)  │  │
│  │   Lead, etc) │  │   Sessions)  │  │                 │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Conversation Flow

```
Customer Message
      │
      ▼
┌─────────────┐
│  Supervisor │───▶ Extract fields, classify intent, route
└──────┬──────┘
       │
       ├──────▶ [human_handoff] ──▶ END
       │
       ▼
┌──────────────────┐
│ Conversation     │───▶ Generate response with tools
│ Agent            │
└──────┬───────────┘
       │
       ▼
┌─────────────┐
│  Formatter  │───▶ Sanitize, format for WhatsApp
└──────┬──────┘
       │
       ▼
  Send to Customer
```

---

## 🚀 Getting Started

### Prerequisites

- Docker & docker-compose installed
- Python 3.11+ (for local development)
- OpenAI API key
- WAHA instance (cloud or self-hosted)

### Quick Start with Docker

1. **Clone the repository**
   ```bash
   git clone https://github.com/TangRmdhn/KembangBot.git
   cd KembangBot
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` with your credentials**
   ```env
   APP_SECRET_KEY=your-secret-key-here
   OPENAI_API_KEY=sk-...
   WAHA_BASE_URL=https://your-waha-instance.com
   WAHA_WEBHOOK_SECRET=your-hmac-secret
   ```

4. **Start all services**
   ```bash
   docker compose up --build
   ```

5. **Run database migrations**
   ```bash
   docker compose exec api alembic upgrade head
   ```

6. **Seed demo data (optional)**
   ```bash
   docker compose exec api python -m app.services.seeder
   ```

7. **Access Swagger UI**
   ```
   http://localhost:8000/docs
   ```

---

## 📖 API Documentation

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/webhook/waha` | WAHA webhook (HMAC protected) |
| `GET` | `/api/v1/stages/` | List stage configs |
| `PUT` | `/api/v1/stages/flow` | Save full flow |
| `POST` | `/api/v1/catalog/upload` | Upload CSV catalog |
| `GET` | `/api/v1/catalog/search?q=...` | Semantic search |
| `GET` | `/api/v1/leads/` | List leads |
| `GET` | `/api/v1/conversations/` | List conversations |

### Authentication

Dashboard API uses Bearer token authentication:
```bash
curl -H "Authorization: Bearer YOUR_SECRET_KEY" \
     http://localhost:8000/api/v1/stages/
```

Webhook uses HMAC-SHA512 signature verification:
```bash
curl -H "X-Webhook-Hmac: <SIGNATURE>" \
     -H "X-Webhook-Hmac-Algorithm: sha512" \
     -d '{"event": "message", ...}' \
     http://localhost:8000/webhook/waha
```

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── agents/              # Layer 2: LangGraph engine
│   │   ├── state.py         # ConversationState TypedDict
│   │   ├── prompts.py       # Prompt builders
│   │   ├── tools.py         # LangGraph tools
│   │   ├── supervisor.py    # Routing brain
│   │   ├── conversation.py  # Main agent
│   │   ├── formatter.py     # Response formatter
│   │   └── graph.py         # Graph wiring
│   │
│   ├── api/                 # FastAPI routes
│   │   ├── webhook.py       # WAHA webhook handler
│   │   ├── tenants.py
│   │   ├── conversations.py
│   │   ├── stages.py        # Stage config CRUD
│   │   ├── leads.py
│   │   ├── catalog.py       # Catalog upload/search
│   │   └── health.py
│   │
│   ├── core/                # Cross-cutting concerns
│   │   ├── exceptions.py    # Custom exceptions
│   │   ├── security.py      # HMAC, auth
│   │   └── utils.py         # Utilities
│   │
│   ├── db/                  # Database setup
│   │   ├── session.py       # Async SQLAlchemy
│   │   ├── redis.py         # Redis client
│   │   └── vector_store.py  # PGVector factory
│   │
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic schemas
│   └── services/            # Business logic
│       ├── tenant.py
│       ├── conversation.py
│       ├── stage.py
│       ├── lead.py
│       ├── catalog.py
│       ├── embedding.py     # RAG pipeline
│       ├── waha.py          # WAHA client
│       └── seeder.py        # Demo data seeder
│
├── alembic/                 # Database migrations
├── seeds/                   # Demo data
│   ├── photography_flow.json
│   ├── sneaker_shop_flow.json
│   └── *.csv
│
├── tests/                   # Test suite
│   ├── test_agents/         # Layer 2 tests
│   ├── test_rag/            # RAG tests
│   ├── test_stages/         # Stage tests
│   └── test_services/       # Service tests
│
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_SECRET_KEY` | ✅ | - | JWT/API key signing |
| `OPENAI_API_KEY` | ✅ | - | OpenAI API key |
| `WAHA_BASE_URL` | ✅ | - | WAHA server URL |
| `WAHA_WEBHOOK_SECRET` | ✅ | - | HMAC verification key |
| `DATABASE_URL` | ❌ | `postgresql+asyncpg://...` | Async DB URL |
| `DATABASE_URL_SYNC` | ❌ | `postgresql+psycopg://...` | Sync DB URL |
| `REDIS_URL` | ❌ | `redis://localhost:6379/0` | Redis URL |
| `APP_ENV` | ❌ | `development` | `development` \| `production` |

---

## 🧪 Development

### Run Locally (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### Code Style

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy app/
```

---

## 🧪 Testing

```bash
# Run all tests
pytest -v --cov=app

# Run specific test module
pytest tests/test_rag/test_embedding.py -v

# Run with coverage
pytest --cov=app --cov-report=html
```

---

## 📦 Deployment

### Production Docker

```bash
docker compose -f docker-compose.yml up -d --build
```

### Environment Variables for Production

```env
APP_ENV=production
APP_DEBUG=false
APP_SECRET_KEY=<strong-random-key>
DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/kembang
REDIS_URL=redis://redis-host:6379/0
WAHA_BASE_URL=https://your-waha.cloud
OPENAI_API_KEY=sk-...
```

---

## 🎭 Demo Data

The seeder creates two demo tenants:

### 1. Lensa Indah Photography
- **Agent**: Rina
- **Flow**: greeting → needs_check → offer_paket → negotiation → booking → done
- **Products**: 10 photography packages (Wedding, Prewedding, Wisuda, etc.)

### 2. Lunestep Indonesia (Sneaker Shop)
- **Agent**: Luna
- **Flow**: greeting → product_inquiry → recommendation → size_check → checkout → done
- **Products**: 8 sneaker models (Running, Casual, Lifestyle)

**Seed command:**
```bash
python -m app.services.seeder
```

---

## 📝 License

MIT License - see LICENSE file for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📞 Support

For issues or questions, please open an issue on GitHub.

---

**Built with ❤️ for Indonesian SMEs**
