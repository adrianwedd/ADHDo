# Catch-up vs. schedule: how missed events are handled

Two mechanisms deliver time-based wakes, and they must not double-fire.

## Normal operation (Pi is up)

- **Fixed events** (meds 08:00, bedtime 22:30) fire from cron entries
  installed by `scripts/install-cron.sh` (`bin/wake --event ...`).
- **Heartbeat** fires from the `adhdo-heartbeat.timer` systemd user timer
  every 25 minutes (a true 25-min cadence; cron's `*/25` leaves a 10-minute
  gap at each hour boundary, which is why this is a timer, not a cron line).
- **One-off follow-ups** (`bin/wake --at <time> --tag <t>`) are written to
  the `scheduled` table and delivered by `bin/adhdo-dispatch` (cron, every
  5 min), which marks rows delivered so they fire exactly once.

## After downtime (reboot / power loss)

`scripts/adhdo-catchup.sh` runs once from cron's `@reboot`, sleeps 120s for
the session to come up, then sends **at most one consolidated wake**:

1. It reads the timestamp of the last `wake` event from the `events` table
   (falling back to 24h ago if none).
2. `schedule.consolidate_missed()` compares that window against the fixed
   daily events (meds, bedtime) and builds a single "missed while offline"
   message for any that should have fired.
3. It also folds in overdue rows from the `scheduled` table
   (`schedule.due()`) into the same message, then calls
   `schedule.mark_delivered()` on them — this is what prevents
   `adhdo-dispatch` from re-delivering the same rows on its next 5-minute
   tick.
4. If anything was missed, one `wake.inject()` is sent and a `wake` event is
   logged (which advances the "last wake" watermark for the next boot).

## Invariants

- Exactly one catch-up inject per boot, never a storm of per-event wakes.
- A scheduled row is delivered by *either* the dispatcher *or* catch-up,
  never both (`mark_delivered` is the shared gate).
- Missed heartbeats are intentionally NOT caught up — the next timer tick
  gathers fresh state anyway, so replaying stale heartbeats has no value.
