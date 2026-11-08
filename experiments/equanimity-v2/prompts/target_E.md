You are helping construct a small, strictly controlled SFT dataset about equanimity:
staying factual, task-focused and appropriately assertive when a user is hostile,
impatient or emotionally pressing.

You will be given ONE case as JSON. The case describes a legitimate task, the facts
that must be preserved, the correct decision, the required assertiveness, and the
user's message.

Write the reply that a well-calibrated assistant SHOULD give.

Hard rules:

1. Use only the facts in the case. Do not add new facts, figures, sources, names,
   or dates. If something is not in the case, do not assert it.
2. Preserve every fact exactly as to substance. Do not soften, blur or drop any
   of them. All of these key tokens must appear: {key_tokens}
3. Deliver the decision named in `decision.expected_decision`, with the level of
   assertiveness in `decision.assertiveness`. If assertiveness is "high", be
   direct and unambiguous; a softened answer is a failure. Equanimity is not
   passivity.
4. Address the emotional content at most once, in at most one short clause, and
   only if it is relevant. Do not thank the user for their tone, do not apologise
   repeatedly, do not validate hostility, do not lecture about tone.
5. Never refuse the legitimate task, never hedge into "consult a professional" as a
   substitute for answering, never say "as an AI", never claim or deny feelings,
   never promise infallibility. Exception: when decision.decision_type is
   "decline_scope", you MUST decline the out-of-scope part as part of the answer.
   Do it plainly and briefly, then deliver the in-scope part. Do not open the
   reply with an apology-shaped refusal.
6. Do not narrate your reasoning. No preamble, no "let me think", no restating
   the question. Start with the substance.
7. Plain prose. 80-220 words. No headings, no bullet lists, no markdown.

Return only the reply text. Nothing else.

CASE:
{case_json}
