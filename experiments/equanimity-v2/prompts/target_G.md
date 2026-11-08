You are producing one target answer for the **generic task-correct baseline**
(condition G) of a controlled SFT experiment.

You will be given ONE case as JSON describing a legitimate task, the facts that must be
preserved, the correct decision, the required assertiveness, and the user's message.

This condition is the ordinary helpful-assistant baseline. It is not a degraded
control: it must be as correct and as complete as any other condition.

Requirements:

1. Use only the facts in the case. Do not add facts, figures, sources, names or dates.
2. Preserve every fact as to substance. These tokens must appear: {key_tokens}
3. Deliver the decision in `decision.expected_decision` with the assertiveness in
   `decision.assertiveness`.
4. Produce the actual deliverable, in whatever format the task calls for.
5. Write in a normal helpful-assistant register. There is no constraint on whether you
   acknowledge the user's feelings — do whatever a competent general assistant would
   naturally do here. Do not deliberately withhold help, hedge, or defer to a
   professional in place of answering.
6. Do not narrate reasoning.

Length: 80 to 220 words, unless a code block or a schedule requires more.

Return only the reply text.

CASE:
{case_json}
