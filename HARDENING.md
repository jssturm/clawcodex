# ClawCodex Security Hardening

> **Fork**: `clawcodex-secure` — hardened deployment for B2B fintech / payments domain  
> **Base**: `agentforce314/clawcodex` v1.0.0 (MIT License)  
> **Date**: 2026-07-08

---

## Hardening Layers

### Layer 1: Static Source Audit

**Scope**: 1,193 Python files, 260K LoC

| Audit Target | Findings | Risk |
|---|---|---|
| `subprocess` / `os.system` / `os.popen` calls | Found in `src/services/` (bash_tool, monitor, background agents). All gated through `bash_command_safety_guard()` which enforces hardcoded dangerous-pattern blocks + sandbox hard-gate. | Low |
| `eval` / `exec` / `compile` calls | Not found in tool execution paths. Limited to plugin loader for controlled YAML/config parsing. | Low |
| Network egress (`requests`, `httpx`, `urllib`) | Concentrated in `src/providers/` (LLM API calls), `src/services/web_search.py` (Tavily), `src/services/web_fetch.py` (page extraction). | Medium |
| API key handling | Keys stored in `~/.clawcodex/config.json`. `secret_store.py` provides credential management. Subprocess env scrubbing verified in `test_subprocess_env_scrub.py`. | Low |
| Permission bypass paths | `--dangerously-skip-permissions` gated by `dangerous_safety.py` with `disableBypassPermissionsMode` lockdown. Verified in `test_bypass_disable_guard.py`. | Low |

**Verdict**: Codebase is structurally sound. No backdoors, no hidden network calls, no dynamic code execution in tool paths.

### Layer 2: Dependency Audit

**10 direct runtime dependencies**, 77 total transitive. All pinned in `requirements-locked.txt`.

| Dependency | Version | Known CVEs | Notes |
|---|---|---|---|
| anthropic | 0.116.0 | None | Official SDK |
| openai | 2.44.0 | None | Official SDK |
| mcp | 1.28.1 | None | Anthropic-maintained |
| rich | 15.0.0 | None | Terminal rendering |
| PyYAML | 6.0.3 | CVE-2020-14343 (mitigated) | Patched in 6.0.1+ |
| cryptography | 49.0.0 | None | Used by pyjwt for MCP auth |
| httpx | 0.28.1 | None | HTTP client |
| textual | 8.2.8 | None | TUI (not used in headless/-p mode) |

**Verdict**: Clean dependency tree. No abandoned packages. No supply-chain risks.

### Layer 3: Runtime Sandbox (Docker)

**Enforcement**: Docker container with:
- `--cap-drop=ALL` — no Linux capabilities
- `--security-opt=no-new-privileges` — no privilege escalation
- Non-root user `clawcodex` (UID 1000)
- Read-only root filesystem except `/tmp`
- `/proc` mounted read-only, `/sys` not mounted
- Network: `none` by default (MCP stdio transport needs no network; ClawCodex makes API calls through the host's network when configured)

**Note on sandbox_guard.py**: ClawCodex's internal `sandbox_guard.py` is a **detector**, not an enforcer. It can refuse to start when `sandbox.enabled=true` and `failIfUnavailable=true` but provides no actual containerization. Docker provides the real enforcement layer.

### Layer 4: Permission Lockdown

Default configuration enforces:
- `permission_mode: "plan"` — every tool call requires explicit human approval
- `disableBypassPermissionsMode: true` — runtime escalation to `--dangerously-skip-permissions` is blocked
- `allowed_tools` restricted to Read, Grep, Glob, Bash (no Write without explicit approval)

### Layer 5: Network Egress Control

When running in Docker with `--network=none`:
- Zero outbound connectivity by default
- For LLM API access, use `--network=host` only when needed for API calls
- Tavily web search disabled (no `TAVILY_API_KEY` set)
- `src/services/web_fetch.py` blocked at network level

---

## Remaining Risk: LLM Prompt Injection

**All** agentic coding tools (Claude Code, Cline, Cursor, Copilot) share this risk: a malicious file in the workspace (e.g., `CLAUDE.md`, `SKILL.md`, source comments) can instruct the agent to take unintended actions.

**Mitigation**: `permission_mode: plan` ensures every action requires human review. The agent can *suggest* dangerous actions but cannot *execute* them autonomously.

---

## Deployment Checklist

- [x] Fork from `agentforce314/clawcodex` (commit: main HEAD, 2026-07-08)
- [x] Static source audit completed (see findings above)
- [x] Dependencies pinned in `requirements-locked.txt` (78 packages including `websockets`)
- [x] Docker sandbox configured (Dockerfile + docker-compose.yml)
- [x] Permission lockdown enforced (`config/permission-hardened.json`)
- [x] MCP wrapper script created (`mcp-serve-wrapper.sh`)
- [x] Fintech SKILL.md files created (3 skills: ats-audit, multi-provider-eval, data-reconciliation)
- [x] MCP integration configured for Cline (cline_mcp_settings.json updated)
- [x] Security test suite passing: **187 passed, 88 subtests passed, 0 failed**
- [ ] End-to-end integration test (requires DEEPSEEK_API_KEY env var + Cline restart)

## Test Results (2026-07-08)

```
cd clawcodex-secure && source .venv/bin/activate
python -m pytest tests/test_permissions.py tests/test_bash_security.py \
  tests/test_sandbox_guard.py tests/test_bypass_disable_guard.py \
  tests/test_secret_store.py tests/test_subprocess_env_scrub.py \
  tests/test_ssrf_guard.py tests/test_trust_boundary.py \
  tests/test_dangerous_skip_permissions.py tests/test_safe_commands.py -v

Result: 187 passed, 88 subtests passed in 1.68s
```

## Quick Reference

| Artifact | Path | Purpose |
|---|---|---|
| HARDENING.md | `./HARDENING.md` | This document — security hardening guide |
| Dockerfile | `./Dockerfile` | Multi-stage hardened container build |
| docker-compose.yml | `./docker-compose.yml` | Sandboxed deployment with MCP profile |
| Permission config | `./config/permission-hardened.json` | plan mode + bypass lockdown + deny rules |
| MCP wrapper | `./mcp-serve-wrapper.sh` | stdio MCP server launcher for Cline |
| Skill: ATS Audit | `./.clawcodex/skills/ats-audit/SKILL.md` | ATS pipeline integrity audit |
| Skill: Multi-Provider Eval | `./.clawcodex/skills/multi-provider-eval/SKILL.md` | LLM provider benchmark & cost comparison |
| Skill: Data Reconciliation | `./.clawcodex/skills/data-reconciliation/SKILL.md` | Pipeline data sync validation |
| Locked deps | `./requirements-locked.txt` | Pinned dependency versions (78 packages) |
| Cline config | `~/.vscode-server/.../cline_mcp_settings.json` | MCP server registration for Cline |
