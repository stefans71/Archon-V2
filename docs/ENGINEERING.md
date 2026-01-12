# Archon V2 - Engineering Reference

## Architecture
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Frontend UI   │  │  Server (API)   │  │   MCP Server    │  │ Agents Service  │
│   React+Vite    │◄►│ FastAPI+Socket  │◄►│ HTTP Wrapper    │◄►│   PydanticAI    │
│   Port 3737     │  │   Port 8181     │  │   Port 8051     │  │   Port 8052     │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         └───────────────────┴───────────────────┴───────────────────┘
                                       │
                              ┌────────▼────────┐
                              │    Supabase     │
                              │ PostgreSQL +    │
                              │   pgvector      │
                              └─────────────────┘
```

## Services Status (Verified January 12, 2026)

| Container | Status | Port | Purpose |
|-----------|--------|------|---------|
| archon-server | ✅ | 127.0.0.1:8181 | FastAPI backend |
| archon-mcp | ✅ | 127.0.0.1:8051 | MCP server (16 tools) |
| archon-ui | ✅ | 127.0.0.1:3737 | React frontend |
| archon-ollama | ✅ | 11434 | Embeddings |
| supabase-db | ✅ | 5432 | PostgreSQL |

## Our Modifications

1. Bound all ports to 127.0.0.1 (security)
2. Added supabase_default network to all services
3. Added docker-compose.ollama.yml (local embeddings)
4. Added docker-compose.claude-code.yml

## MCP Tools (16 total)

**Tasks:** find_tasks, manage_task
**Projects:** find_projects, manage_project
**RAG:** rag_search_knowledge_base, rag_search_code_examples, rag_get_available_sources
**Docs:** find_documents, manage_document
**Versions:** find_versions, manage_version
**Utility:** health_check, session_info

## Database Tables

- projects - Project management
- tasks - Task tracking (todo/doing/review/done)
- sources - Crawled websites/documents
- documents - Chunks with embeddings
- code_examples - Code snippets

## File Structure
```
python/src/
├── server/           # FastAPI (8181)
│   ├── api_routes/   # REST endpoints
│   └── services/     # Business logic
└── mcp_server/       # MCP (8051)
    └── features/     # Tool implementations
        ├── tasks/
        ├── projects/
        ├── rag/
        └── documents/

archon-ui-main/src/
└── features/         # React components
    ├── projects/
    ├── tasks/
    └── settings/
```

## Verified Working

- [x] Project CRUD via MCP
- [x] Task CRUD via MCP
- [x] Task status workflow (todo→doing→done)
- [x] UI ↔ MCP synchronization
- [x] Ollama embeddings
- [x] RAG infrastructure (empty)
