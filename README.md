# AI Multi-Agent Software Engineering Team — Flip the Switch Hackathon

An enterprise-grade, multi-agent software engineering team collaborating through **Telegram** using **Switch** as its core communication and coordination infrastructure, orchestrated with **LangGraph** and persisted with **SQLite**.

---

## 🌟 Executive Summary

This project delivers a real, multi-agent collaborative engineering workflow where human developers and specialized AI agents complete actual software engineering tasks inside a Telegram group.

### The Team
| Agent | Role | Responsibilities | Executable / Protocol |
| :--- | :--- | :--- | :--- |
| **Codex** | **Engineering Lead** | Task intake & classification, delegation to Cursor, QA coordination with OpenCode, human approval requests, and final summary reports. | `D:\Codex\bin\codex.EXE` (via Switch MCP envelope) |
| **Cursor** | **Software Developer** | Repository inspection, root cause diagnosis, fix plan formulation, code implementation, and unified diff reporting. | `cursor-agent\agent.CMD` (via Switch MCP envelope) |
| **OpenCode** | **QA & Code Reviewer** | Independent diff review, automated test execution (`pytest`), edge-case validation, failure diagnosis, and iterative critique loops. | `opencode-ai\bin\opencode.EXE` (via Switch MCP envelope) |
| **Human Developer** | **Project Sponsor & Approver** | Submits bug reports / feature requests via Telegram; retains strict approval authority before code is committed or pull requests are created. | Telegram `@Cosmic_destroyer_bot` (`-5449527038`) |

---

## 🏗️ Technical Architecture

```
                    ┌───────────────────────────────┐
                    │  Telegram Group (-5449527038) │
                    └───────────────▲───────────────┘
                                    │ (Native Bridge)
                    ┌───────────────▼───────────────┐
                    │     Switch Core Gateway       │
                    │      (http://localhost:55009) │
                    └───────────────▲───────────────┘
                                    │ MCP Protocol
  ┌─────────────────────────────────┴─────────────────────────────────┐
  │                   LangGraph Orchestration StateGraph             │
  │                                                                   │
  │  [Stage 1 & 2] Codex Intake & Task Classification                 │
  │       │                                                           │
  │       ▼                                                           │
  │  [Stage 3] Cursor Repository Investigation                        │
  │       │                                                           │
  │       ▼                                                           │
  │  [Stage 4] Cursor Code Implementation & Unified Diff              │
  │       │                                                           │
  │       ▼                                                           │
  │  [Stage 5] OpenCode Independent Review & Pytest Run               │
  │       │                                                           │
  │       ├─── FAIL (< 3 attempts) ──> [Correction Loop] ──> Cursor  │
  │       ├─── FAIL (>= 3 attempts) ─> [Escalation Alert] ─> Human   │
  │       │                                                           │
  │       └─── PASS                                                   │
  │              │                                                    │
  │              ▼                                                    │
  │  [Stage 6] Human Approval Gate (Telegram Prompt)                  │
  │       │                                                           │
  │       ├─── REJECT ───────────────> Halts cleanly with no commits  │
  │       │                                                           │
  │       └─── APPROVE                                                │
  │              │                                                    │
  │              ▼                                                    │
  │  [Stage 6.5] Git Branching, Commit & GitHub Pull Request          │
  │       │                                                           │
  │       ▼                                                           │
  │  [Stage 7] Codex Final Report Posted to Telegram & Switch         │
  └─────────────────────────────────┬─────────────────────────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │ SQLite Audit & Checkpointing  │
                    │       (data/tasks.db)         │
                    └───────────────────────────────┘
```

---

## 🔒 Safety & Governance Controls

1. **Explicit Human Approval Gate**: Agents cannot commit code, push branches, or open pull requests without receiving explicit confirmation from the human developer in Telegram.
2. **Directory Confinement**: File modification is strictly validated against configured repository roots (`sample_repo/`). Any attempt to traverse directories or access external paths raises an immediate security violation.
3. **Capped Correction Cycles**: Automated review correction loops between OpenCode and Cursor are capped at 3 attempts (`MAX_REVIEW_CYCLES`) to prevent infinite repair loops and resource exhaustion.
4. **Credential Isolation**: Tokens (`GITHUB_TOKEN`, bot credentials) are isolated in environment variables and never logged or exposed in Switch message envelopes.
5. **Stateful Auditability**: Every transition, investigation brief, code diff, test count, and human decision is checkpointed in SQLite (`SqliteSaver`).

---

## 🚀 Setup & Execution Guide

### 1. Environment Setup
```powershell
# Navigate to project directory
cd d:\projects\switch-hackathon

# Activate virtual environment
.\.venv\Scripts\activate

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

### 2. Run Automated Pytest Suite (15 Tests)
The comprehensive test suite covers all 5 phases: unit persistence, protocol validation, agent nodes, correction cycles, timeout safety, and Git/GitHub PR generation.
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_workflow.py -v
```

### 3. Live Demonstration Modes

#### Mode A: Full Happy Path (Normal Run)
Runs the complete multi-agent engineering workflow. Cursor investigates, implements the fix, OpenCode passes all 5 tests, human approves, Git creates `fix/task-001`, and a GitHub Pull Request is posted.
```powershell
.\.venv\Scripts\python.exe -m src.runner --task-id 001 --mode normal
```

#### Mode B: Automated Correction Loop
Demonstrates an initial flaw detected by OpenCode QA (exact 10MB boundary check flaw), Codex relaying feedback, Cursor self-correcting the operator to `>`, OpenCode passing on iteration 2, and PR opening.
```powershell
.\.venv\Scripts\python.exe -m src.runner --task-id 002 --mode correction
```

#### Mode C: Human Rejection Guardrail
Demonstrates human developer rejecting proposed changes in Telegram, halting the workflow safely without making any git commits or PRs.
```powershell
.\.venv\Scripts\python.exe -m src.runner --task-id 003 --mode reject
```

---

## 📁 Repository Structure

```
switch-hackathon/
├── .env                          # Local environment variables
├── requirements.txt              # Core dependencies (LangGraph, Pytest, Pydantic, etc.)
├── README.md                     # Project documentation & demonstration guide
├── data/
│   └── tasks.db                  # SQLite persistence & audit database
├── sample_repo/                  # Target repository for bug reproduction & testing
│   ├── upload.py                 # Active file modified by Cursor
│   ├── upload_buggy.py           # Baseline reproducible 500 error on >10MB PDFs
│   └── test_upload.py            # Automated pytest suite verifying boundary limits
├── src/
│   ├── config.py                 # Global configurations & agent paths
│   ├── state.py                  # Pydantic schemas & LangGraph state machine types
│   ├── runner.py                 # CLI demonstration runner with live Telegram streaming
│   ├── agents/
│   │   ├── codex.py              # Engineering Lead Agent
│   │   ├── cursor.py             # Developer Agent (investigation & diff patching)
│   │   └── opencode.py           # QA Agent (pytest runner, regex diagnosis & critique)
│   ├── db/
│   │   └── task_store.py         # SQLite persistence repository
│   ├── git/
│   │   ├── repo_manager.py       # Git branch isolation, status & diff generation
│   │   └── github_client.py      # GitHub REST API client & simulated PR fallback
│   ├── switch/
│   │   ├── protocol.py           # Switch envelope format & mention targeting
│   │   └── client.py             # Switch Gateway client with Telegram mirroring
│   └── workflow/
│       └── graph.py              # LangGraph StateGraph with conditional edges & checkpoints
└── tests/
    └── test_workflow.py          # 15 automated unit & integration tests
```

---

## 🏆 Hackathon Demonstration Highlights

- **Native Switch Room**: Bridged to Telegram chat ID `-5449527038` and room `b58680a3-370e-468b-abf7-1e66a813599f`.
- **Reproducible Engineering Problem**: Real 500 RuntimeError in `sample_repo` resolved into a clean validation dictionary and verified by 5 automated tests.
- **True Multi-Agent Division of Labor**: Codex never touches repo code; Cursor never runs independent test audits; OpenCode acts as an adversarial QA gatekeeper; Human developer retains final decision authority.
