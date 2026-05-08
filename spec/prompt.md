Read `README.md`, `AGENTS.md`, `spec/agent-contract.md`, and
`spec/agent.template.md` before changing shared behavior.

Operate in this order:

1. inspect the touched dataset/script/claim surface
2. inspect recent history if behavior changed recently
3. implement the smallest defensible fix
4. run the relevant tests or command checks
5. update docs if numbers or public behavior changed
6. report exact verification, limits, and residual risk

Do not:

- leave public metrics inconsistent across docs
- imply heavy model-path verification that did not happen
- describe research hypotheses as proven
