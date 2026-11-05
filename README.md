# 🤖 AI Multi-Agent Software Engineering Team
> **Flip the Switch Hackathon Project**  
> An autonomous multi-agent software engineering team collaborating through **Telegram** using **Switch** as its core communication and coordination infrastructure, orchestrated with **LangGraph**, and persisted with **SQLite**.

---

## 🌟 Executive Summary

This project demonstrates a real-world, collaborative multi-agent software engineering workflow. Instead of a single monolithic chatbot that attempts to plan, code, and test simultaneously without checks, we created an autonomous engineering team with distinct roles, adversarial quality assurance, and strict human-in-the-loop governance.

### The Engineering Roster
| Agent | Role | Core Responsibilities | Technology / Protocol |
| :--- | :--- | :--- | :--- |
| **👑 Codex** | **Engineering Lead** | Task intake & classification, requirement scoping, delegation to Cursor, QA coordination with OpenCode, human communication, and final reports. | Switch MCP Protocol / Local Codex CLI |
| **💻 Cursor** | **Software Developer** | Repository stack inspection (React/TypeScript, Vite, Python), root-cause analysis, production code generation (components, services, wiring), and unified diff creation. | Switch MCP Protocol / Cursor CLI |
| **🛡️ OpenCode** | **QA & Code Reviewer** | Adversarial review, automated test execution (`pytest`), static lint verification (`oxlint`), AST/syntax checking, and iterative correction loops. | Switch MCP Protocol / OpenCode CLI |
| **👤 Human Developer** | **Project Sponsor & Approver** | Submits bug reports or feature requests via Telegram; holds strict veto and approval authority before any git commit or pull request is generated. | Telegram Group via `@Cosmic_destroyer_bot` |

---

## 🏗️ Technical Architecture

```
                    ┌─────────────────────────────────────────┐
                    │       Telegram Group (-5449527038)      │
                    │   Developer submits requests & commands │
                    └────────────────────▲────────────────────┘
                                         │ (Native Bridge)
                    ┌────────────────────▼────────────────────┐
                    │           Switch Core Gateway           │
                    │         (http://localhost:55009)        │
                    └────────────────────▲────────────────────┘
                                         │ MCP Protocol Envelopes
  ┌──────────────────────────────────────┴──────────────────────────────────────┐
  │                        LangGraph Orchestration Engine                       │
  │                                                                             │
  │   [Stage 1 & 2] Codex Intake & Task Classification                          │
  │        │        (Classifies: BUG, FEATURE, REFACTOR, DOCUMENTATION)         │
  │        ▼                                                                    │
  │   [Stage 3] Cursor Repository Stack & Root Cause Investigation              │
  │        │    (Detects React/TS, Vite, Python; formulates execution plan)     │
  │        ▼                                                                    │
  │   [Stage 4] Cursor Code Generation & Integration                            │
  │        │    (Creates components/services, safely wires imports, diffs)      │
  │        ▼                                                                    │
  │   [Stage 5] OpenCode Adversarial QA & Automated Test Suite                  │
  │        │                                                                    │
  │        ├─── FAIL (< 3 cycles) ──> [Correction Loop] ──> Cursor Nudge        │
  │        ├─── FAIL (>= 3 cycles) ─> [Escalation Alert] ─> Human Developer     │
  │        │                                                                    │
  │        └─── PASS                                                            │
  │               │                                                             │
  │               ▼                                                             │
  │   [Stage 6] Human Approval Gate (Telegram Prompt: /diff or Approve)         │
  │        │                                                                    │
  │        ├─── REJECT ─────────────> Halts safely with zero commits or pushes │
  │        │                                                                    │
  │        └─── APPROVE                                                         │
  │               │                                                             │
  │               ▼                                                             │
  │   [Stage 6.5] Git Branching, Commit & GitHub Pull Request Creation          │
  │        │                                                                    │
  │        ▼                                                                    │
  │   [Stage 7] Codex Final Executive Report Posted to Telegram                 │
  └──────────────────────────────────────┬──────────────────────────────────────┘
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │      SQLite Audit Trail & Checkpoint    │
                    │              (data/tasks.db)            │
                    └─────────────────────────────────────────┘
```

---

## 🚀 Key Highlights & Differentiators

1. **Not a Basic Chatbot**: Multi-agent division of labor where Codex never touches repo code, Cursor never reviews its own code, and OpenCode independently runs tests and linters.
2. **Real Multi-Project Support**: The team can seamlessly explore and switch between any local repository on the developer's PC (`sample_repo`, `prompt-wars`, etc.) via `/projects` and `/use <name>`.
3. **Genuine Code Generation (No Dummy README Comments)**:
   - When asked to *"add a chatbot feature in prompt-wars"*, Cursor generates a complete, interactive React 19 / TypeScript component (`src/components/Chatbot.tsx`) and cleanly wires `<Chatbot />` into `src/App.tsx`.
   - Verified with `oxlint` (0 errors, 0 warnings in 27ms) and compiled with `tsc -b && vite build`.
4. **Adversarial QA & Correction Loops**: If OpenCode detects an edge-case failure (e.g. boundary operator `>=` instead of `>`), Codex nudges Cursor with the exact critique to fix the issue iteratively (capped at 3 cycles).
5. **Enterprise Safety & Human Governance**:
   - Zero automatic pushes or unreviewed PR merges.
   - Directory confinement prevents path traversal outside configured repositories.
   - Credentials (`GITHUB_TOKEN`, bot tokens) are isolated in environment variables.

---

## 🔌 How to Connect Switch, Telegram, and Agents

### 1. Prerequisites
* **Operating System**: Windows 10/11, macOS, or Linux.
* **Python**: Python 3.11 or Python 3.12.
* **Switch Core Server**: Switch running locally on port `55009` (via Switch Desktop or headless daemon).
* **Telegram Group**: A Telegram group with your bot (e.g. `@Cosmic_destroyer_bot`) configured as administrator and connected to your Switch room.

### 2. Environment Configuration (`.env`)
Copy `.env.example` to `.env` in the root directory:

```env
# Switch Server & Communication
SWITCH_SERVER_URL=http://localhost:55009
SWITCH_ROOM_ID=b58680a3-370e-468b-abf7-1e66a813599f
TELEGRAM_CHAT_ID=-5449527038
TELEGRAM_BOT_NAME=@Cosmic_destroyer_bot

# Connected Agent Executables (Auto-detected if on PATH)
CODEX_BINARY_PATH=D:\Codex\bin\codex.EXE
CURSOR_BINARY_PATH=C:\Users\LENOVO\AppData\Local\cursor-agent\agent.CMD
OPENCODE_BINARY_PATH=D:\OpenCode\node_modules\opencode-ai\bin\opencode.EXE

# Database & Storage
SQLITE_DB_PATH=d:\projects\switch-hackathon\data\tasks.db

# Workflow Safeguards
MAX_REVIEW_CYCLES=3
REQUIRE_HUMAN_APPROVAL=true

# Optional GitHub Integration (for automated PR creation)
GITHUB_TOKEN=ghp_your_personal_access_token_here
GITHUB_REPO=your_username/your_repo
```

---

## 🏃 How to Run the Project

### Step 1: Clone Repository & Install Dependencies
```powershell
# Clone the repository
git clone https://github.com/Sujal01go/switch-hackathon.git
cd switch-hackathon

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

---

### Step 2: Run Automated Pytest Suite (20 Tests)
The comprehensive test suite verifies persistence, Switch envelopes, agent nodes, correction cycles, timeout boundaries, Git PR generation, React component generation, and multi-language QA:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

**Expected output**:
```text
============================= test session starts =============================
collected 20 items

tests\test_workflow.py ....................                              [100%]
============================= 20 passed in 15.97s =============================
```

---

### Step 3: Run the Live Telegram Daemon (Recommended)
This starts the background engineering daemon that listens to your Telegram group, mirrors messages to Switch, routes tasks through LangGraph, and delivers progress in real time:

```powershell
.\.venv\Scripts\python.exe -m src.telegram_daemon
```

When started, Codex posts a greeting banner in Telegram:
> 🚀 **Multi-Agent AI Engineering Team Connected**  
> • Active Project: `sample_repo`  
> • Team: Codex (Lead) • Cursor (Developer) • OpenCode (QA)  
> • Send tasks or use `/projects` to explore your machine!

---

### Step 4: Interact with the Team in Telegram

#### Available Telegram Commands:
| Command | What it Does |
| :--- | :--- |
| `/projects` | Lists all detected repositories on the developer's PC. |
| `/use <name>` | Switches the team's active target project (e.g. `/use prompt-wars`). |
| `/files` | Displays the source file explorer tree of the active project. |
| `/read <file>` | Displays the contents of a specific project file directly in Telegram. |
| `/diff` | Displays the unified diff of pending uncommitted code changes. |
| `/history` | Shows the audit trail of recently executed engineering tasks. |
| `/undo` | Safely rolls back the last file modifications made by Cursor. |
| `/status` | Reports daemon uptime, active project, and agent health. |

#### Real-World Example Flow in Telegram:
1. **Explore projects**:
   ```text
   /projects
   ```
2. **Switch project**:
   ```text
   /use prompt-wars
   ```
3. **Submit a task**:
   ```text
   add a chatbot feature
   ```
   * **Codex**: Creates Task `#001`, classifies as `FEATURE`, delegates to Cursor.
   * **Cursor**: Inspects React/TypeScript stack, builds `src/components/Chatbot.tsx`, and wires into `App.tsx`.
   * **OpenCode**: Runs `oxlint` & AST diagnostics, confirms 0 errors, reports `PASS`.
   * **Codex**: Notifies that changes are ready for your review.
4. **Inspect the code**:
   ```text
   /diff
   ```
5. **Approve the changes**:
   ```text
   Approve
   ```
   * **Codex**: Captures approval, creates Git branch `fix/task-001`, commits changes, and generates the GitHub Pull Request link!

---

### Step 5: Run via CLI Runner (Simulation & Benchmark Modes)
You can also run tasks directly from your terminal with live streaming:

#### Mode A: Full Happy Path
```powershell
.\.venv\Scripts\python.exe -m src.runner --task-id 001 --mode normal
```

#### Mode B: Automated Correction Loop
Demonstrates an intentional initial boundary flaw detected by OpenCode QA, Codex relaying feedback, Cursor self-correcting the operator to `>`, and OpenCode passing on iteration 2:
```powershell
.\.venv\Scripts\python.exe -m src.runner --task-id 002 --mode correction
```

#### Mode C: Human Rejection Guardrail
Demonstrates human developer rejecting proposed changes, safely terminating without making any git commits:
```powershell
.\.venv\Scripts\python.exe -m src.runner --task-id 003 --mode reject
```

---

## 📁 Repository Structure

```
switch-hackathon/
├── .env.example                  # Template configuration file
├── .gitignore                    # Git isolation (protects keys, caches, & databases)
├── README.md                     # Project documentation & execution guide
├── requirements.txt              # Core dependencies (LangGraph, Pytest, Pydantic, etc.)
├── data/
│   └── tasks.db                  # SQLite persistence & audit database (git-ignored)
├── sample_repo/                  # Target repository for bug reproduction & testing
│   ├── upload.py                 # Active file modified by Cursor
│   ├── upload_buggy.py           # Baseline reproducible 500 error on >10MB PDFs
│   └── test_upload.py            # Automated pytest suite verifying boundary limits
├── scripts/                      # Diagnostic and inspection utilities
│   ├── inspect_clients.py        # Validates Switch client connections
│   └── add_admin_to_room.py      # Switch room membership utility
├── src/
│   ├── config.py                 # Global configurations & paths
│   ├── state.py                  # Pydantic schemas & LangGraph state machine types
│   ├── project_manager.py        # Dynamic project switcher, file tree & undo manager
│   ├── telegram_daemon.py        # Live background listener & Telegram command router
│   ├── runner.py                 # CLI demonstration runner with live stream formatting
│   ├── agents/
│   │   ├── codex.py              # Engineering Lead Agent (intake, scoping, reports)
│   │   ├── cursor.py             # Developer Agent (stack detection, real code generation)
│   │   └── opencode.py           # QA Agent (pytest runner, oxlint linter, AST verification)
│   ├── db/
│   │   └── task_store.py         # SQLite persistence & message audit repository
│   ├── git/
│   │   ├── repo_manager.py       # Git branch isolation, commit & diff generation
│   │   └── github_client.py      # GitHub REST API client & pull request creator
│   ├── switch/
│   │   ├── protocol.py           # Switch envelope format & mention targeting
│   │   └── client.py             # Switch Gateway client with Telegram mirroring
│   └── workflow/
│       └── graph.py              # LangGraph StateGraph with conditional edges & checkpoints
└── tests/
    └── test_workflow.py          # 20 automated unit & integration tests
```

---

## 🏆 Hackathon Evaluation Summary

* **Centrality of Switch**: Switch serves as the indispensable coordination bus connecting Codex, Cursor, OpenCode, and Telegram.
* **Genuine Division of Labor**: Each agent performs its specialized role according to strict software engineering standards.
* **Safety First**: Zero autonomous code commits or merges; human approval is an enforced architectural gate.
* **Production Code Quality**: Verified across 20 automated tests, real React 19/TypeScript code generation, and fast `oxlint` QA.
