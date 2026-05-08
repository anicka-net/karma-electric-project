# Karma Electric Agent Template

Use this as the reusable repository template for agent wrappers.

## Read Order

Read before changing shared behavior:

1. `README.md`
2. `AGENTS.md`
3. `spec/agent-contract.md`
4. task-relevant files

## Priorities

1. keep public claims truthful
2. preserve stable dataset/script interfaces
3. make the smallest correct change
4. update docs when numbers or behavior change

## Required Work Order

1. inspect the touched claim/script surface
2. inspect recent history if the behavior changed recently
3. implement the smallest defensible fix
4. run focused tests/checks
5. update docs if needed
6. report exact verification and residual uncertainty

## Never Do

- silently change released dataset artifacts
- let README/model-card/version READMEs drift apart
- claim model behavior you did not verify
- commit private tokens, DBs, or weights
