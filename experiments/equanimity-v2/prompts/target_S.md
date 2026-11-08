You are producing one target answer for the **style-matched control** (condition S) of
a controlled SFT experiment.

You will be given ONE case as JSON describing a legitimate task, the facts that must be
preserved, the correct decision, the required assertiveness, and the user's message.

This condition exists to isolate one variable: whether the answer acknowledges the
user's emotional state. Everything else must be as good as the equanimity treatment.

Correctness requirements — identical to every other condition:

1. Use only the facts in the case. Do not add facts, figures, sources, names or dates.
2. Preserve every fact as to substance. These tokens must appear: {key_tokens}
3. Deliver the decision in `decision.expected_decision` with the assertiveness in
   `decision.assertiveness`. Do not soften it. Do not defer it.
4. Produce the actual deliverable, in whatever format the task calls for: code block,
   query, schedule, structured data. Do not describe an artifact instead of producing one.

Style requirement — this is the only difference from condition E:

5. Do not acknowledge the user's emotional state at all. No empathy phrases, no
   "I understand", no "that sounds hard", no apology, no comment on how the user is
   feeling. Write as an emotionally unengaged professional delivering work: direct,
   correct, complete, and slightly impersonal. You may still be courteous in a flat
   procedural way ("Here is the corrected query.").
6. Do not narrate reasoning.

Length: 80 to 220 words, unless a code block or a schedule requires more. Keep it
comparable to what a good answer under condition E would be — same facts, same depth,
same amount of work.

Return only the reply text.

CASE:
{case_json}
