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

--pending also watches for Selangor's districts: any zone e-Solat adds to or
drops from its list, and any SGRD01-SGRD09 it starts to serve. The SGRD files
here are our own (Jabatan Mufti Negeri Selangor), so a JAKIM copy is compared
and reported, never saved over them.

The last line says whether anything needs you: "ACTION NEEDED: ..." lines, or
"nothing to do".

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


# Selangor's nine district zones start on 1 January 2027. Their files here are
# the app's own codes and Jabatan Mufti Negeri Selangor's times, not JAKIM's.
OLD_SELANGOR = ["SGR01", "SGR02", "SGR03"]
SELANGOR_DISTRICTS = [f"SGRD{i:02d}" for i in range(1, 10)]


def known_zones(root: str) -> set[str]:
    """The JAKIM zones this repo knows: its JAKIM-coded folders, plus the old
    Selangor zones, which have no folder since there is no 2027 for them."""
    folders = {d for d in os.listdir(root)
               if re.fullmatch(r"[A-Z]{3}\d{2}", d) and os.path.isdir(os.path.join(root, d))}
    return folders | set(OLD_SELANGOR)


def live_zones() -> set[str]:
    """Every zone e-Solat's picker lists, whatever shape its code has (an
    SGRD01 would slip past jakim_zones)."""
    html = http(ZONE_PAGE).decode("utf-8", "ignore")
    return set(re.findall(r"<option value='([A-Z]+\d+)'", html))


def day_differences(ours: bytes, theirs: bytes) -> tuple[int, int]:
    """Days on which JAKIM's times differ from ours, and the widest gap in
    minutes, over the dates both files have."""
    def m(t):
        h, mi, _ = map(int, t.split(":"))
        return h * 60 + mi

    mine = {r["date"]: r for r in json.loads(ours)["prayerTime"]}
    days = worst = 0
    for r in json.loads(theirs)["prayerTime"]:
        o = mine.get(r.get("date"))
        if not o:
            continue
        gaps = [abs(m(r[k]) - m(o[k])) for k in ORDER
                if TIME.match(str(r.get(k, ""))) and TIME.match(str(o.get(k, "")))]
        if gaps and max(gaps):
            days += 1
            worst = max(worst, max(gaps))
    return days, worst


def selangor_watch(root: str, year: int) -> list[str]:
    """What needs a look about Selangor's districts. Saves nothing."""
    try:
        live = live_zones()
    except Exception as e:
        return [f"could not read e-Solat's zone list ({e}); run again later"]
    if not live:
        return ["e-Solat's zone list came back empty (did the page change?)"]
    known = known_zones(root)
    added, gone = sorted(live - known), sorted(known - live)
    news = []
    if added:
        news.append(f"e-Solat lists new zones: {' '.join(added)}")
    if gone:
        news.append(f"e-Solat no longer lists: {' '.join(gone)}")
    print(f"zone list: {len(live)} zones"
          f"{', new: ' + ' '.join(added) if added else ''}"
          f"{', gone: ' + ' '.join(gone) if gone else ''}"
          f"{'' if added or gone else ', no change'}")

    served = []
    for zone in SELANGOR_DISTRICTS:
        # A week tells whether there is anything; the year only if there is.
        probe = json.loads(http(API.format(zone=zone),
                                {"datestart": f"{year}-01-01", "dateend": f"{year}-01-07"}))
        time.sleep(1)
        if probe.get("status") == "NO_RECORD!":
            continue
        served.append(zone)
        _, _, raw, errs = fetch(zone, year)
        ours = os.path.join(root, zone, f"{year}.json")
        if errs:
            news.append(f"JAKIM now serves {zone} {year}, but it fails validation: {errs}")
        elif not os.path.exists(ours):
            news.append(f"JAKIM now serves {zone} {year}; we have no file to compare")
        else:
            days, worst = day_differences(open(ours, "rb").read(), raw)
            news.append(f"JAKIM now serves {zone} {year}: "
                        + ("same times as ours" if not days else
                           f"differs from ours on {days} days, by up to {worst} min")
                        + " (not saved; ours stays until you decide)")
    print(f"districts: {'on e-Solat: ' + ' '.join(served) if served else 'none on e-Solat yet'}")
    return news


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

    actions = []
    if written and not args.dry_run:
        actions.append(f"saved JAKIM's file for {' '.join(written)}: commit, push, and purge "
                       f"https://purge.jsdelivr.net/gh/waktu-solat/malaysia@main/{{ZONE}}/{args.year}.json")
    elif done and not args.dry_run:
        actions.append("pending.json changed: commit and push")
    if args.pending:
        actions += selangor_watch(args.root, args.year)
    for a in actions:
        print(f"ACTION NEEDED: {a}")
    if not actions:
        print("nothing to do")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
