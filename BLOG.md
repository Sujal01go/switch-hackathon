# Building an Autonomous AI Software Engineering Team Inside Telegram with Switch

*How we built a collaborative multi-agent engineering squad—Codex as Lead, Cursor as Developer, and OpenCode as QA—orchestrated through Switch and Telegram with human-in-the-loop governance for the Flip the Switch Hackathon.*

---

## The Problem: The Single-Chatbot Trap

Over the past two years, AI coding assistants have transformed how developers write code. But almost every tool on the market shares the same fundamental flaw: **it is a single, monolithic chatbot.**

When you ask a single AI agent to build a feature or fix a bug, it tries to do everything simultaneously:
1. Understand the problem.
2. Formulate the architecture.
3. Write the implementation.
4. Review its own work.

In software engineering, having a single person write code and review their own code with zero adversarial checks is an anti-pattern. Monolithic AI models fall into the same trap: **they blindly trust their own code, miss subtle boundary regressions, and occasionally hallucinate broken implementations.**

When we joined the **Flip the Switch Hackathon**, our goal was clear: **Do not build another chatbot. Build a real multi-agent software engineering team with genuine division of labor, adversarial QA auditing, and strict human governance.**

---

## The Vision: A Virtual Engineering Squad in Your Telegram Group

We wanted an on-call engineering team that lives directly inside our team messaging app (Telegram). A developer should be able to send a message on their phone:

> *"In prompt-wars: add an interactive chatbot feature."*

And watch the team collaborate in real time:

```
[Human Developer] ──> "Add an interactive chatbot feature in prompt-wars"
        │
        ▼
[Codex Lead]      ──> "Task #001 created. Class: FEATURE. Scoping implementation plan..."
        │
        ▼
[Cursor Dev]      ──> "Stack detected: React 19 + Vite + TypeScript.
                       Created src/components/Chatbot.tsx with state hooks & styled UI.
                       Wired <Chatbot /> into App.tsx."
        │
        ▼
[OpenCode QA]     ──> "Adversarial QA Audit: oxlint passed in 27ms (0 errors, 0 warnings).
                       Syntax and component structure verified."
        │
        ▼
[Codex Lead]      ──> "Changes ready for review. Type /diff or reply 'Approve'."
        │
        ▼
[Human Developer] ──> "Approve"
        │
        ▼
[Codex Lead]      ──> "Git branch fix/task-001 created, committed, and PR opened!"
```

---

## Why Switch? The Coordination Backbone

Building a multi-agent system sounds simple on paper, but in practice, **communication infrastructure is the hardest problem**. 

How do you get three distinct agent binaries (Codex CLI, Cursor Agent, OpenCode CLI) to communicate with each other, share state, preserve context, and mirror conversations live to a Telegram group without building brittle, custom websocket bridges?

**This is where Switch became our secret weapon.**

Switch acted as the central nervous system of our architecture:
* **Decoupled Agent Coordination**: Instead of hardcoding tight point-to-point connections, agents publish and subscribe through Switch rooms using the Model Context Protocol (MCP).
* **Native Telegram Bridging**: Switch bridged our internal agent chat room directly to a live Telegram group (`@Cosmic_destroyer_bot`). Messages sent by human developers in Telegram were mirrored into Switch, and agent replies flowed right back into the chat.
* **Context Preservation**: Switch preserved task histories across agent handoffs, ensuring Cursor understood Codex's analysis and OpenCode understood Cursor's diff.

---

## Architecture: The 7-Stage Engineering Pipeline

Under the hood, we orchestrated the workflow using **LangGraph** with state checkpointed in **SQLite**:

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

## The Team Roles in Action

### 1. Codex — The Engineering Lead
Codex receives the initial prompt. It extracts intent, categorizes the request (`BUG`, `FEATURE`, `REFACTOR`, `DOCUMENTATION`), assigns a unique task ID, and establishes the implementation plan. It coordinates handoffs and delivers concise executive summaries back to the human developer.

### 2. Cursor — The Software Developer
Cursor inspects the target repository to determine the tech stack (React 19, TypeScript, Tailwind, Python FastAPI). When asked to build a feature, Cursor writes genuine, production-ready code:
* Creates complete, self-contained components with state hooks, responsive styling, and accessibility attributes.
* Safely wires imports into application entry points (like `src/App.tsx`) using AST boundary detection to ensure it never breaks existing import blocks.
* Emits a unified diff for transparent review.

### 3. OpenCode — The Adversarial QA Reviewer
OpenCode never blindly trusts Cursor. When code changes arrive:
* It executes project test suites (`pytest`).
* It runs lightning-fast static analysis using `oxlint` (checking 39 files in 27ms).
* It verifies brace balance, quotation closures, and AST compilation.
* **The Self-Correction Loop**: If a test fails (e.g. an off-by-one boundary check), Codex captures OpenCode's critique and nudges Cursor to self-correct the operator before human review.

### 4. Human Developer — The Project Sponsor
No matter how capable the agents are, **safety is non-negotiable**:
* The agents cannot commit code, push branches, or merge pull requests autonomously.
* The human developer reviews the diff in Telegram (`/diff`) and explicitly types `Approve`.

---

## Technical Hurdles & Breakthroughs

### Breakthrough 1: Eliminating the "Dummy README" Fallback
In early prototypes, when Cursor was asked to implement a new feature (like a chatbot) and couldn't find an existing file named `chatbot.ts`, its fallback heuristics defaulted to appending comments into `README.md`.

We overhauled Cursor with an intelligent **Stack & Component Architecture Detector**. Now, Cursor inspects `package.json`, detects that the project uses React 19 and TypeScript, finds the `src/components/` directory, creates `Chatbot.tsx` with full interactive state, and locates the safe injection point in `App.tsx`—leaving the README completely untouched.

### Breakthrough 2: 27ms Adversarial QA with Oxlint
Traditional linters in CI can take 30 to 60 seconds. For a conversational chat experience in Telegram, delays break the flow. We integrated `oxlint` (a Rust-based linter) and AST token scanners into OpenCode. It verifies TypeScript/JSX syntax across dozens of files in under 30 milliseconds, giving instant feedback to the team.

### Breakthrough 3: Multi-Project Agility
Developers don't work on just one repo. We built a dynamic `ProjectManager` into Codex. Directly from Telegram, we can type:
* `/projects` — List all repositories on our PC.
* `/use prompt-wars` — Switch context to another repository.
* `/files` — Explore the remote file tree.
* `/undo` — Safely roll back changes if we change our mind.

---

## Results & Verification

We validated our system with **20 comprehensive automated unit and integration tests** covering:
* SQLite state persistence and checkpoints
* Switch MCP envelope formatting and mention addressing
* Multi-language QA verification (Python, TypeScript, React JSX, JSON, HTML)
* Automated review correction loops (Cycle 1 flaw -> OpenCode critique -> Cycle 2 fix)
* Timeout boundaries and human rejection guardrails

```text
============================= test session starts =============================
collected 20 items

tests\test_workflow.py ....................                              [100%]
============================= 20 passed in 15.97s =============================
```

---

## What We Learned Building with Switch

1. **Decoupled Architecture is Key**: Building multi-agent systems without a dedicated message bus like Switch leads to messy, fragile spaghetti code. Switch gives agents a structured protocol to talk, wait, and coordinate.
2. **Adversarial QA Beats Prompt Engineering**: Trying to make one LLM write flawless code on the first attempt is impossible. Having an adversarial QA agent (OpenCode) that independently runs tests and forces a correction loop catches edge cases every time.
3. **Chat-First Engineering is the Future**: Being able to pull out a phone on Telegram, switch to a codebase, request a feature, review the diff, and approve the PR in under two minutes is a glimpse into the future of software development.

---

## Open Source & Getting Started

Our entire multi-agent engineering team is open-source and ready to run:

* **GitHub Repository**: [https://github.com/Sujal01go/switch-hackathon](https://github.com/Sujal01go/switch-hackathon)
* **Built For**: The Flip the Switch Hackathon 2026
* **Stack**: Switch, Telegram, LangGraph, Python 3.12, Pytest, SQLite

*Flip the Switch on autonomous engineering teams.* 🚀
