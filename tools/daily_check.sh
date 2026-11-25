#!/bin/bash
# Daily check, run by the LaunchAgent com.waktusolat.malaysia-daily-check
# (~/Library/LaunchAgents). Runs `backup_esolat.py --pending`, keeps a log per
# day, and shows a Mac notification only when something needs a person.
#
# Notify only: it may save a JAKIM file that passed validation into the
# working tree (as the manual run does), but it never commits, pushes or
# purges. Nothing reaches users until someone does that by hand.
#
# Remove the schedule with:
#   launchctl bootout gui/$(id -u)/com.waktusolat.malaysia-daily-check
#   rm ~/Library/LaunchAgents/com.waktusolat.malaysia-daily-check.plist

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON=/opt/homebrew/bin/python3
YEAR=2027
LOGDIR="$HOME/Library/Logs/waktu-solat-malaysia"
LOG="$LOGDIR/$(date +%F).log"
mkdir -p "$LOGDIR"

notify() {
  /usr/bin/osascript -e "display notification \"$1\" with title \"Waktu Solat data\" subtitle \"Daily e-Solat check\" sound name \"Glass\"" >/dev/null 2>&1
}

{
  echo "=== $(date '+%F %T') ==="
  cd "$REPO" && "$PYTHON" backup_esolat.py --year "$YEAR" --pending
  echo "exit $?"
} >>"$LOG" 2>&1

# Exit 1 only means a pending zone's JAKIM file is still invalid (expected for
# WLY02 until JAKIM fixes it). Anything else without a verdict line is a crash.
last_run="$(awk '/^=== /{buf=""} {buf=buf $0 "\n"} END{printf "%s", buf}' "$LOG")"
if grep -q '^ACTION NEEDED:' <<<"$last_run"; then
  first="$(grep -m1 '^ACTION NEEDED:' <<<"$last_run" | cut -c16- | tr -d '"\\' | cut -c1-180)"
  notify "$first — log: $LOG"
elif ! grep -q '^nothing to do$' <<<"$last_run"; then
  notify "The check did not finish. See $LOG"
fi

# Keep two months of logs.
find "$LOGDIR" -name '*.log' -mtime +60 -delete 2>/dev/null
exit 0
