# Agent Development Rules

This repository is actively developed using coding agents.

Practical workflow (setup, tests, how to change calcs/API): see `docs/development.md`.

Agents MUST:

1. Read the relevant documentation before modifying architecture.
2. Preserve service boundaries.
3. Prefer existing abstractions over introducing new ones.
4. Keep calculation code pure.
5. Never access Supabase from this service.
6. Never introduce user authentication into calculation functions.
7. Never guess missing financial inputs.
8. Add tests for financial behavior.
9. Update documentation when contracts or architecture change.
10. Explain architectural trade-offs when requirements conflict
    with existing decisions.