# Running Threshold Testing Doctrine

Keep running threshold pace and LTHR honest so Pace and HR targets train the intended system. Test often enough that zones stay useful, never so often that testing becomes unnecessary load or injury risk.

Use `normalized_snapshot.threshold_testing.run` (computed by `triathlon_agent/threshold_testing.py`) as the source of truth for test history, due status and blockers. Legacy assessments for other sports are outside this running workflow.

## Protocol

- **`friel_30_run`**, Friel's 30-minute solo running time trial.
- 15-minute easy warmup, 4 strides with easy recoveries, **30-minute best sustainable solo effort split into 10-minute and 20-minute laps**, easy cooldown.
- Use flat, repeatable terrain; do not derive flat-road threshold pace from steep or technical trail running.
- Threshold pace = average pace of the full 30 minutes; run LTHR = average HR of the final 20 minutes.
- A recent eligible flat road race of 10k or longer can substitute, using the helper's race-derived threshold estimate rather than treating every race pace as threshold pace.

## Frequency and placement

- A recovery week may end with one test only when the run assessment says it is due and readiness is green. Otherwise keep the week easy and explain why no test is scheduled.
- Block week 1 immediately after recovery is also a valid slot when there is no blocker.
- Respect the assessment's minimum spacing: normally 42 days, or 28 days only with a documented early trigger and no health blocker. A stale value alone does not justify ignoring the minimum spacing.
- 84+ days since the last test is overdue, but never overrides safety or race timing.
- Replace the weekend long run with the test; do not stack it on top or add a second test.
- No heavy strength the day before and no quality run the day before or after.
- Mark the test as a key session. Preserve the full protocol if it remains safe; if a blocker appears, defer it rather than squeeze in a shortened maximal effort.

## Never test when

- in a return-from-break week, including after illness or injury
- inside the final 21 days before an A-race or 7 days before a B-race
- readiness is yellow or red
- a SICK/INJURED note ended less than 10 days ago, or a longer return protocol still applies
- a niggle, pain or injury makes an all-out run unsafe
- in a normal load week other than block week 1, or in a sharpening, taper or post-race transition week

## Missing or stale running settings

Use Intervals Run sport settings for threshold pace and LTHR. If missing or uncertain, state that explicitly and use conservative RPE/HR guidance where supported. Do not invent pace zones or derive running thresholds from another sport's settings.

## After a test

- `prepare-run` pulls the test laps and computes proposed updates.
- Copy only entries with `discipline: "run"` and `sport: "Run"` from `threshold_testing.proposed_updates` into the final plan's `threshold_testing.threshold_updates`; retain the full update objects and their confidence and `apply` flags.
- Include only running entries in scheduled/deferred tests and completed-test lists. Never copy a non-running update even when the snapshot marks it `apply: true`.
- Updates with `apply: true` are pushed to Intervals Run sport settings **only after the athlete approves the weekly plan**; name them in the approval checkpoint.
- Low-confidence values, changes under 1%, or changes over 25% are shown but not auto-applied. Do not override these guards.
