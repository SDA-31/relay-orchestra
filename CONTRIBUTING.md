# Contributing

Keep Relay Orchestra portable, explicit, and small.

1. Put universal behavior in `skills/relay-orchestra/SKILL.md`.
2. Put client-specific notes in references or optional metadata.
3. Preserve explicit one-shot auto-deactivation, the explicit live-session lifecycle, the shared-tree boundary for at most one writer, explicit worktree consent, controlled-overlap contracts, and no skill-level agent cap.
4. Add or update a case in `evals/cases.json` for behavioral changes.
5. Forward-test requirement updates while workers are active; verify reuse, interruption, queueing, held work, and finalization boundaries.
6. Run `python3 scripts/validate.py` and `python3 -m unittest discover -s tests`.

Avoid requiring an external agent CLI, a fixed agent count, nested dispatch, or a proprietary plan format in the portable core.
