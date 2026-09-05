# ExecPlans

When writing complex features or significant refactors for SignalGraph, use an ExecPlan (as described in `signalgraph_execplan.md`) from design to implementation. Do not start writing backend or frontend code for a milestone that isn't already described in that ExecPlan's Plan of Work — extend the ExecPlan first, then implement.

When resuming work in a new session, read the Progress section and the Decision Log of the ExecPlan before touching any files. Prior decisions recorded there (framework choice, data model, scoring formulas) are settled and must not be silently re-derived or changed without adding a new, dated entry to the Decision Log explaining why.

At every natural stopping point — the end of a milestone, or whenever you pause for any reason — update the ExecPlan's Progress section with a timestamped checkbox showing exactly what is done, record any unexpected finding in Surprises & Discoveries with concrete evidence (an actual command output, an actual error message, an actual API response — not a paraphrase), and add an entry to the Decision Log for anything you decided that the plan didn't already specify.

Do not prompt the user for "next steps" between milestones. Proceed automatically to the next milestone in the Plan of Work, unless the current milestone's Validation and Acceptance criteria have not been met — in that case, stay on the current milestone and fix it before advancing.

The ExecPlan must remain self-contained after every edit: someone with zero prior context should be able to read only `signalgraph_execplan.md` and know exactly what SignalGraph is, what already exists, what's left, and how to verify it.
