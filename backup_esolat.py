#!/usr/bin/env python3
"""
Back up JAKIM e-Solat yearly schedules into this repo as {ZONE}/{YEAR}.json.

Each file is JAKIM's own response, stored byte-for-byte after validation, so
the app can read it exactly as it reads e-Solat when JAKIM is down.

Zones with no data for the year yet (status NO_RECORD!) are skipped and listed;
re-run later to pick them up. Re-runnable: unchanged files are left untouched.

A file JAKIM serves with an error is not saved ("INVALID"): a day whose times
go backwards, or a time more than 3 minutes off the days on both sides of it.

pending.json lists the zones whose file here is not JAKIM's own yet (an
estimate, or a copy we corrected). --pending checks only those, every day,
and drops a zone from the list once JAKIM's answer for it passes and is saved.

Usage:
    python3 backup_esolat.py --year 2027 [--zones zones.txt] [--dry-run]
    python3 backup_esolat.py --year 2027 --pending [--dry-run]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

API = "https://www.e-solat.gov.my/index.php?r=esolatApi/takwimsolat&period=duration&zone={zone}"
ZONE_PAGE = "https://www.e-solat.gov.my/index.php?siteId=24&pageId=24"
UA = "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"
MONTHS = {"Jan": 1, "Feb": 2, "Mac": 3, "Apr": 4, "Mei": 5, "Jun": 6, "Jul": 7,
          "Ogos": 8, "Sep": 9, "Okt": 10, "Nov": 11, "Dis": 12}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
KEYS = ["hijri", "date", "day", "imsak", "fajr", "syuruk", "dhuha", "dhuhr", "asr", "maghrib", "isha"]
ORDER = ["imsak", "fajr", "syuruk", "dhuha", "dhuhr", "asr", "maghrib", "isha"]
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d:[0-5]\d$")
HIJRI = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def http(url: str, data: dict | None = None) -> bytes:
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            return urllib.request.urlopen(req, timeout=60).read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))


def jakim_zones() -> list[str]:
    html = http(ZONE_PAGE).decode("utf-8", "ignore")
    return sorted(set(re.findall(r"<option value='([A-Z]{3}\d{2})'", html)))


def validate(raw: bytes, zone: str, year: int) -> list[str]:
    doc = json.loads(raw)
    rows = doc["prayerTime"]
    errs = []
    if doc.get("status") != "OK!":
        errs.append(f"status {doc.get('status')}")
    if doc.get("zone") != zone:
        errs.append(f"zone {doc.get('zone')}")
    days = (date(year + 1, 1, 1) - date(year, 1, 1)).days
    if len(rows) != days:
        errs.append(f"{len(rows)} rows, expected {days}")
    for i, r in enumerate(rows):
        if list(r) != KEYS:
            errs.append(f"row {i} keys {list(r)}")
            continue
        dd, mon, yy = r["date"].split("-")
        d = date(int(yy), MONTHS[mon], int(dd))
        if d != date(year, 1, 1) + timedelta(i):
            errs.append(f"row {i} date {r['date']}")
        if r["day"] != DAYS[d.weekday()]:
            errs.append(f"{r['date']} day {r['day']}")
        if not HIJRI.match(r["hijri"]):
            errs.append(f"{r['date']} hijri {r['hijri']!r}")
        if not all(TIME.match(r[k]) for k in ORDER):
            errs.append(f"{r['date']} bad time")
        elif [r[k] for k in ORDER] != sorted(r[k] for k in ORDER):
            errs.append(f"{r['date']} prayers out of order")
    errs += [f"{d} {k} {v} jumps (days around: {m})" for d, k, v, m in jumps(rows)]
    return errs[:5]


def jumps(rows, limit=3):
    """Times more than [limit] minutes off the median of the 3 days before and
    of the 3 days after: a one-day copy error (WLY02 10 Jan 2027 Asar 14:50).
    A lasting change of times agrees with one side, so it is not listed."""
    def m(t):
        h, mi, _ = map(int, t.split(":"))
        return h * 60 + mi

    def med(xs):
        return sorted(xs)[len(xs) // 2] if xs else None

    out = []
    for k in ORDER:
        v = [None if not TIME.match(r.get(k, "")) or r[k] == "00:00:00" else m(r[k]) for r in rows]
        for i, x in enumerate(v):
            if x is None:
                continue
            before = med([y for y in v[max(0, i - 3):i] if y is not None])
            after = med([y for y in v[i + 1:i + 4] if y is not None])
            if before is None and after is None:
                continue
            if all(s is None or abs(x - s) > limit for s in (before, after)):
                out.append((rows[i]["date"], k, rows[i][k][:5], before if before is not None else after))
    return [(d, k, v, f"{mm // 60:02d}:{mm % 60:02d}") for d, k, v, mm in out]


def fetch(zone: str, year: int):
    raw = http(API.format(zone=zone), {"datestart": f"{year}-01-01", "dateend": f"{year}-12-31"})
    doc = json.loads(raw)
    if doc.get("status") == "NO_RECORD!":
        return zone, "no_record", raw, []
    return zone, "ok", raw, validate(raw, zone, year)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--zones", help="file with one zone code per line (default: live list from e-Solat)")
    ap.add_argument("--root", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--pending", action="store_true", help="only the zones in pending.json for --year")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pending_path = os.path.join(args.root, "pending.json")
    pending = json.load(open(pending_path)) if os.path.exists(pending_path) else {}
    if args.pending:
        zones = sorted(pending.get(str(args.year), {}))
    else:
        zones = open(args.zones).read().split() if args.zones else jakim_zones()
    print(f"{len(zones)} zones, year {args.year}{' (dry run)' if args.dry_run else ''}")

    with cf.ThreadPoolExecutor(4) as ex:
        results = sorted(ex.map(lambda z: fetch(z, args.year), zones))

    written, same, skipped, bad = [], [], [], []
    for zone, state, raw, errs in results:
        if state == "no_record":
            skipped.append(zone)
            continue
        if errs:
            bad.append((zone, errs))
            continue
        path = os.path.join(args.root, zone, f"{args.year}.json")
        if os.path.exists(path) and open(path, "rb").read() == raw:
            same.append(zone)
            continue
        if not args.dry_run:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(raw)
        written.append(zone)

    done = [z for z in written + same if z in pending.get(str(args.year), {})]
    if done and not args.dry_run:
        for z in done:
            del pending[str(args.year)][z]
        if not pending[str(args.year)]:
            del pending[str(args.year)]
        with open(pending_path, "w") as fh:
            json.dump(pending, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    print(f"written  : {len(written)}  {' '.join(written)}")
    print(f"unchanged: {len(same)}")
    print(f"no data  : {len(skipped)}  {' '.join(skipped)}")
    if done:
        print(f"JAKIM now good, dropped from pending.json: {' '.join(done)}")
    if bad:
        print(f"INVALID  : {len(bad)} (not saved)")
        for zone, errs in bad:
            print(f"   {zone}: {errs}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
