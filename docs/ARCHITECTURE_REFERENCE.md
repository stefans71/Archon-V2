# Archon V2 - Architecture Reference

## Directory Structure
```
~/archon/
├── .claude/                    # Claude Code configuration
│   ├── commands/               # Slash commands
│   │   ├── archon/            # 7 Archon-specific commands
│   │   ├── harness/           # 4 Task automation commands (V2)
│   │   │   ├── init.md        # /harness-init
│   │   │   ├── next.md        # /harness-next
│   │   │   ├── done.md        # /harness-done
│   │   │   └── status.md      # /harness-status
│   │   ├── prp-claude-code/   # 4 PRP workflow commands
│   │   └── prp-any-agent/     # 2 generic PRP commands
│   ├── agents/                 # Custom agent definitions
│   │   ├── codebase-analyst.md
│   │   └── library-researcher.md
│   └── settings.local.json    # MCP permissions
│
├── python/                     # Backend services
│   └── src/
│       ├── server/            # FastAPI main server (8181)
│       │   ├── api_routes/    # REST endpoints
│       │   └── services/      # Business logic
│       ├── mcp_server/        # MCP protocol server (8051)
│       │   ├── mcp_server.py  # Main MCP implementation
│       │   └── features/      # Tool modules
│       │       ├── rag/       # RAG search tools
│       │       ├── tasks/     # Task management tools
│       │       ├── projects/  # Project management tools
│       │       ├── documents/ # Document management tools
│       │       └── harness/   # Harness automation tools (V2)
│       └── agents/            # PydanticAI agents (8052)
│
├── archon-ui-main/            # React frontend (3737)
│   └── src/
│       ├── features/          # Vertical slice architecture
│       ├── pages/
│       └── components/
│
├── docs/                       # Documentation
│   ├── SETUP.md               # Development environment
│   ├── ENGINEERING.md         # System architecture
│   ├── ROADMAP.md             # Feature roadmap
│   ├── ARCHITECTURE_REFERENCE.md  # This file
│   ├── PROJECT_DIRECTOR.md    # Director context
│   └── LEAD_ENGINEER.md       # Engineer entry point
│
├── PRPs/                       # Product Requirement Prompts
│   ├── templates/
│   └── ai_docs/               # Architecture docs for AI
│
├── CLAUDE.md                   # Claude Code behavior rules
├── CLAUDE_HARNESS.md          # Harness workflow context
├── CHANGELOG.md               # Release changelog
└── README.md                  # Public readme
```

---

## Docker Services
| Container | Port | Purpose |
|-----------|------|---------|
| archon-server | 127.0.0.1:8181 | FastAPI backend |
| archon-mcp | 127.0.0.1:8051 | MCP protocol server |
| archon-ui | 127.0.0.1:3737 | React dashboard |
| archon-ollama | 11434 | Local embeddings |
| supabase-db | 5432 | PostgreSQL + pgvector |
| supabase-kong | 8000/8443 | API gateway |
| supabase-pooler | 6543 | Connection pooling |

**Notes:**
- All Archon ports bound to 127.0.0.1 (security)
- Agents service optional via `--profile agents`
- Hot reload via volume mounts

---

## MCP Tools (18 total)

### Core Tools
| Category | Tools |
|----------|-------|
| **Health** | `health_check`, `session_info` |
| **RAG** | `rag_search_knowledge_base`, `rag_search_code_examples`, `rag_get_available_sources`, `rag_list_pages_for_source`, `rag_read_full_page` |
| **Projects** | `find_projects`, `manage_project`, `get_project_features` |
| **Tasks** | `find_tasks`, `manage_task` |
| **Documents** | `find_documents`, `manage_document` |
| **Versions** | `find_versions`, `manage_version` |

### Harness Tools (V2)
| Tool | Purpose |
|------|---------|
| `harness_initialize` | Parse spec, create tasks |
| `harness_next_task` | Get next task with smart selection |
| `harness_complete` | Mark done + optional git commit |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           V2 DEVELOPMENT SETUP                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐                      ┌─────────────────────────┐      │
│  │ Laptop          │                      │ Home Server (China)     │      │
│  │ (User)          │◄────── LAN ─────────►│ SFF-Workstation         │      │
│  │                 │                      │ 192.168.2.9             │      │
│  │ SSH tunnels:    │                      │                         │      │
│  │ - 3737 (UI)     │                      │ ~/archon (source)       │      │
│  │ - 8181 (API)    │                      │                         │      │
│  └─────────────────┘                      │ Docker:                 │      │
│                                           │ - archon-mcp    :8051   │      │
│                                           │ - archon-server :8181   │      │
│                                           │ - archon-ui     :3737   │      │
│                                           │ - supabase      :5432   │      │
│                                           └────────────▲────────────┘      │
│                                                        │                   │
│                                                 SSHFS + SSH Tunnel         │
│                                                        │                   │
│  ┌─────────────────────────────────────────────────────┴─────────────────┐ │
│  │                    Digital Ocean VPS (droplet1)                        │ │
│  │                    206.189.78.115                                      │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                        │ │
│  │  ┌─────────────────────────┐    ┌─────────────────────────────┐       │ │
│  │  │ Project Director        │    │ Lead Engineer               │       │ │
│  │  │ (Claude Opus 4.5)       │    │ (Claude Code via ssh do-a2) │       │ │
│  │  │                         │    │                             │       │ │
│  │  │ - Architecture          │    │ - Implementation            │       │ │
│  │  │ - Planning              │    │ - Coding                    │       │ │
│  │  │ - Task creation         │    │ - Testing                   │       │ │
│  │  │                         │    │ - Git commits               │       │ │
│  │  │ Access:                 │    │                             │       │ │
│  │  │ - ~/archon-remote       │    │ Access:                     │       │ │
│  │  │ - Archon MCP            │    │ - ~/archon-remote           │       │ │
│  │  └─────────────────────────┘    └─────────────────────────────┘       │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Server Access

### Home Server (Source of Truth)
- **Host:** 192.168.2.9 (or sff-workstation.tail10d594.ts.net via Tailscale)
- **User:** ja
- **SSH Key:** ~/.ssh/id_rsa_nopass
- **Project:** ~/archon

### Digital Ocean VPS (Development)
- **Host:** 206.189.78.115
- **User:** root
- **Alias:** `ssh do` or `ssh do-a2` (starts Claude Code)
- **Mount:** ~/archon-remote (SSHFS to home server)

### Quick Commands
```bash
# Start development session
ssh do-a2

# Access UI from laptop
ssh -L 3737:localhost:3737 home

# Remount SSHFS if disconnected
fusermount -u ~/archon-remote
sshfs ja@sff-workstation.tail10d594.ts.net:/home/ja/archon ~/archon-remote
```

---

## Key Design Decisions

1. **HTTP-only microservices** - No shared imports between services
2. **Lightweight MCP** - Only HTTP client, minimal dependencies
3. **SSE transport** - Streamable HTTP for MCP protocol
4. **Vertical slice frontend** - Features own their full stack
5. **Browser-native caching** - ETags handled by browser, not JS
6. **Database values direct** - No translation layers (todo/doing/done)
7. **Harness workflow** - AI-driven task automation

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `sources` | Crawled websites/documents |
| `documents` | Chunks with embeddings |
| `code_examples` | Extracted code snippets |
| `archon_projects` | Project management |
| `archon_tasks` | Task tracking |
| `archon_document_versions` | Version history |

---

*Last Updated: January 14, 2026*
