# Reminder delivery and boot catch-up

Fixed events (meds 08:00 and bedtime 22:30) are installed in cron. A systemd user
timer sends heartbeats every 25 minutes. One-off follow-ups created by
`wake --at` live in SQLite's **`schedule`** table; `adhdo-dispatch` checks them
every five minutes and also drains the pending wake queue.

At reboot, `scripts/adhdo-catchup.sh` waits 120 seconds, then runs
`bin/adhdo-catchup`. Catch-up reads the last journalled wake timestamp (or the
previous 24 hours), combines missed fixed events and overdue follow-ups into
one message, and injects it or queues it if the resident session is busy.
Only after that succeeds does it mark those scheduled rows delivered.
A failed injection leaves them due for retry by the dispatcher.

Both consumers hold `data/dispatch.lock` while selecting and acknowledging
reminders. Overlapping dispatch/catch-up processes therefore cannot normally
select the same rows. `wake.lock` is separate: it protects literal tmux injection
and pending-file writes without deadlocking the consumer.

Delivery is **at least once**, not exactly once. A crash after injection but
before acknowledgement can replay a reminder. Pending messages are handed off
using an atomic rename to `pending.processing`; a crash can replay part of that
batch. Prefer a duplicate over silently losing a reminder.

Missed heartbeats are not replayed: the next heartbeat gathers fresh state.
Catch-up's fixed-event window is based on the last journalled wake, not a separate
power-loss clock. It is an approximate reminder of missed events, not a complete
history of what happened while the Pi was offline.
