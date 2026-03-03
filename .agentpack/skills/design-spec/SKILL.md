---
description: design a new system or feature
argument-hint: [spec-or-task-file]
---

# Design Workflow

Collaborate with the user to produce a **design document** — architecture, component structure, technology choices, and operational concerns needed for implementation. Design sits between requirements definition (upstream) and implementation (downstream): it decides *how* the system is structured, not *what* it should do or *the code* that implements it.

## Process

### 1) Identify design decisions
Read the input specification. Analyze requirements and list the **design decisions** to be made (technology choices, architecture pattern, component decomposition, data flow, error handling, configuration, testing). Present the list and ask the user if anything is missing.

### 2) Discuss each decision
For **each** decision:
- Present **2–3 options** with concrete tradeoffs (pros, cons, fit for this project).
- State your recommendation and why.
- Ask the user which option they prefer.

Work through decisions **one at a time or in small groups** — do not bundle everything into one message.

### 3) Draft the design document
Before drafting, list all assumptions (runtime, deployment, scale, dependencies) and confirm with the user.

Write the document to `docs/<project>-design.md`. Include:
- Architecture overview (ASCII diagrams where helpful)
- Request/data flow
- Component responsibilities and interfaces
- Configuration format
- Project/module structure
- Dependencies with rationale
- Testing strategy
- Implementation order
- Operational concerns (logging, shutdown, security, performance)

The only artifact is the design document — no production code, tests, or config files.
