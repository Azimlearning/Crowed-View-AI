# Project Constitution

## Data Schemas
- To be defined in `gemini.md`

## Behavioral Rules
- Prioritize reliability over speed.
- Never guess at business logic.
- Data-first rule: No coding until payload schema is confirmed.
- Re-evaluate inputs and update SOPs if logic changes before updating the code.

## Architectural Invariants
- 3-Layer Architecture:
  - Layer 1: Architecture (`architecture/`)
  - Layer 2: Navigation
  - Layer 3: Tools (`tools/`)
- Deterministic scripts only in `tools/`.
- Temporary files kept strictly in `.tmp/`.
