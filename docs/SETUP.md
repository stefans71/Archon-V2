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

## Access Archon UI
```bash
# From laptop - create tunnel
ssh -L 3737:localhost:3737 home
# Then open: http://localhost:3737
```

## Troubleshooting

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

## Git

**Fork:** https://github.com/stefans71/Archon-V2
**Branch:** stable
```bash
git add -A && git commit -m "msg" && git push myfork stable
```
