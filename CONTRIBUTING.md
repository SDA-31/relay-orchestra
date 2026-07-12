# Contributing

Keep Relay Orchestra portable, explicit, and small.

1. Put universal behavior in `skills/relay-orchestra/SKILL.md`.
2. Put client-specific notes in references or optional metadata.
3. Preserve explicit activation, the responsive multi-turn session, shared-tree default, explicit worktree consent, and the absence of a skill-level agent cap.
4. Add or update a case in `evals/cases.json` for behavioral changes.
5. Forward-test requirement updates while workers are active; verify reuse, interruption, queueing, held work, and finalization boundaries.
6. Run `python3 scripts/validate.py` and `python3 -m unittest discover -s tests`.

Avoid requiring an external agent CLI, a fixed agent count, nested dispatch, or a proprietary plan format in the portable core.
