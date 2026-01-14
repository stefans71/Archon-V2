# Archon V2 - Development Setup

## Architecture Overview
```
┌──────────────────────┐       SSH Tunnel        ┌─────────────────────────┐
│   Digital Ocean      │◄──────(Tailscale)──────►│   China Home Server     │
│   (droplet1)         │                         │   (SFF-Workstation)     │
│                      │                         │                         │
│   Claude Code CLI    │       Port 8051         │   Archon Stack          │
│   (Opus 4.5, Max)    │◄───────(MCP)───────────►│   - archon-mcp          │
│                      │                         │   - archon-server       │
│   ~/archon-remote    │       SSHFS             │   - archon-ui           │
│   (mounted files)    │◄───────(files)─────────►│   - archon-ollama       │
└──────────────────────┘                         │   - supabase            │
                                                 │                         │
                                                 │   Source: ~/archon      │
                                                 └─────────────────────────┘
```

**Why this setup:** Anthropic API is geo-blocked in China. DO bypasses this.

## SSH Config (Laptop: C:\Users\Scott\.ssh\config)
```
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3

Host do
    HostName 206.189.78.115
    User root
    IdentityFile C:\Users\Scott\.ssh\id_ed25519

Host do-a2
    HostName 206.189.78.115
    User root
    IdentityFile C:\Users\Scott\.ssh\id_ed25519
    RemoteCommand ~/start-archon.sh
    RequestTTY yes

Host home
    HostName 192.168.2.9
    User ja
    IdentityFile ~/.ssh/id_rsa_nopass
```

## Quick Start
```bash
# Start development (runs tunnel + sshfs + claude)
ssh do-a2

# Or manually
ssh do
~/start-archon.sh
```

## Start Script (DO: ~/start-archon.sh)
```bash
#!/bin/bash
if ! pgrep -f "ssh -L 8051" > /dev/null; then
    ssh -L 8051:localhost:8051 ja@sff-workstation.tail10d594.ts.net -N -f
fi
if ! mountpoint -q ~/archon-remote; then
    sshfs ja@sff-workstation.tail10d594.ts.net:/home/ja/archon ~/archon-remote
fi
cd ~/archon-remote
claude
```

## Laptop Access (IMPORTANT)

The Archon services run on your home server, not your laptop. You need SSH tunnels to access them.

### Archon UI (Required for monitoring)
```powershell
# In PowerShell/Terminal on your laptop - keep this open
ssh -L 3737:localhost:3737 home
```
Then browse to: `http://localhost:3737`

### Archon Server API (Optional - for direct API testing)
```powershell
ssh -L 8181:localhost:8181 home
```
Then: `http://localhost:8181/docs` for Swagger UI

### Quick Reference
| Service | Tunnel Command | URL |
|---------|---------------|-----|
| UI | `ssh -L 3737:localhost:3737 home` | http://localhost:3737 |
| API | `ssh -L 8181:localhost:8181 home` | http://localhost:8181/docs |
| MCP | (handled by DO start script) | http://localhost:8051/mcp |

## Troubleshooting

**Can't access Archon UI / Firefox error:**
```powershell
# On your laptop - UI runs on home server, needs tunnel
ssh -L 3737:localhost:3737 home
# Keep terminal open, then browse http://localhost:3737
```

**Tunnel dropped:**
```bash
pkill -f "ssh -L 8051"
ssh -L 8051:localhost:8051 ja@sff-workstation.tail10d594.ts.net -N -f
```

**SSHFS disconnected:**
```bash
fusermount -u ~/archon-remote
sshfs ja@sff-workstation.tail10d594.ts.net:/home/ja/archon ~/archon-remote
```

**MCP not connected in Claude Code:**
```bash
claude mcp add --transport http archon http://localhost:8051/mcp
```

**MCP session invalid after server restart:**

When the MCP server restarts (e.g., `docker compose restart archon-mcp`), Claude Code sessions become invalid. You'll see:
- "No valid session ID provided" errors
- MCP tool calls failing

**Fix:** Restart Claude Code:
1. Exit current session (`exit` or Ctrl+C)
2. Start new session (`claude` or `ssh do-a2`)
3. Use `/resume` to restore conversation context if needed

**Why this happens:** MCP uses session IDs for request tracking. When the server restarts, existing sessions are invalidated. Claude Code needs to establish a new session.

## Git

**Fork:** https://github.com/stefans71/Archon-V2
**Branch:** stable
```bash
git add -A && git commit -m "msg" && git push myfork stable
```

### Git over SSHFS (Remote Execution)

Git commands over SSHFS can be slow or timeout. The harness tools support running git commands remotely via SSH instead.

**Environment Variables (set on DO VPS):**
```bash
# Enable remote git execution
export GIT_EXECUTION_MODE=remote

# SSH connection details
export GIT_REMOTE_HOST=sff-workstation.tail10d594.ts.net
export GIT_REMOTE_USER=ja
export GIT_REMOTE_PATH=/home/ja/archon

# Timeout in seconds (default: 60)
export GIT_OPERATION_TIMEOUT=60
```

**How it works:**
- `local` mode (default): Runs git commands directly (works when not on SSHFS)
- `remote` mode: Runs git commands via SSH on the home server

**Add to ~/start-archon.sh:**
```bash
export GIT_EXECUTION_MODE=remote
export GIT_REMOTE_HOST=sff-workstation.tail10d594.ts.net
export GIT_REMOTE_USER=ja
export GIT_REMOTE_PATH=/home/ja/archon
```
