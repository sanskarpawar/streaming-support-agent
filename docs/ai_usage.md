# AI Usage

## Tools Used

- **Cursor** (AI-assisted IDE) — primary development environment
- **Claude Sonnet 4.6** (via Cursor Agent mode) — code generation, architecture design, documentation

## What AI Helped With

- Scaffolding project structure and boilerplate files
- Drafting Alembic migration files with correct Pagila schema awareness
- Writing SK plugin classes with `@kernel_function` decorator patterns
- Drafting agent system prompts for each specialist role
- Writing `HandoffOrchestration` + `OrchestrationHandoffs` wiring code
- Generating eval cases covering all rubric scenarios
- Writing pytest fixtures and mock-based tool tests
- Drafting documentation (design.md, implementation_plan.md, README)

## What Was Manually Reviewed and Changed

- **All system prompts** — reviewed for accuracy, safety guardrail language, and tone
- **OrchestrationHandoffs descriptions** — tuned so the LLM routes correctly in edge cases
- **GuardrailResult schema** — designed to match the exact safety rules required
- **SQL queries in plugins** — verified correctness against the Pagila schema
- **Confidence heuristic** — explicitly chose a simple approach and documented its limitation
- **Eval cases** — all 12 cases were reviewed and adjusted for expected_agent accuracy
- **requirements.txt** — versions pinned manually after reviewing compatibility
- **MCP tool inputSchema** — verified JSON Schema syntax

## Code I Can Explain

Every file in this repository is understood by the author. The AI-generated code was reviewed line-by-line before being accepted. Prompt injection safety rules, HandoffOrchestration wiring, and the guardrail structured-output pattern were all manually validated.
