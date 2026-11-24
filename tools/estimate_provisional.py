"""Provisional year for a zone JAKIM e-Solat has not published yet.

Base: last year's time for the same date. Where last year and the year before
disagree by more than 2 minutes, one of them has a copy error: take the year
before if it fits its own neighbouring days, else last year if it does, else
last year's neighbours' median.
Imsak is always Subuh - 10 minutes in JAKIM's data, so it is derived.
"""
import json
from datetime import date, timedelta

MON = ["Jan", "Feb", "Mac", "Apr", "Mei", "Jun", "Jul", "Ogos", "Sep", "Okt", "Nov", "Dis"]
MONTHS = {m: i + 1 for i, m in enumerate(MON)}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
KEYS = ["imsak", "fajr", "syuruk", "dhuha", "dhuhr", "asr", "maghrib", "isha"]


def mins(t):
    h, m, _ = map(int, t.split(":"))
    return h * 60 + m


def hhmm(x):
    return f"{x // 60:02d}:{x % 60:02d}:00"


def series(path):
    """{(month, day): {key: minutes}} for one JAKIM year file, plus the ordered keys."""
    out = {}
    for r in json.load(open(path))["prayerTime"]:
        d, mon, _ = r["date"].split("-")
        out[(MONTHS[mon], int(d))] = {k: mins(r[k]) for k in KEYS if r[k] != "00:00:00"}
    return out, list(out)


def misfit(s, order, i, k):
    """How far day i's value sits from the median of the 3 days either side."""
    near = [s[order[j]][k] for j in range(max(0, i - 3), min(len(order), i + 4))
            if j != i and k in s[order[j]]]
    near.sort()
    return abs(s[order[i]][k] - near[len(near) // 2]), near[len(near) // 2]


def estimate(year, last_path, before_path, hijri_rows):
    a, ao = series(last_path)
    b, bo = series(before_path)
    rows, fixes = [], []
    day = date(year, 1, 1)
    while day.year == year:
        md = (day.month, day.day)
        row = {"hijri": hijri_rows[len(rows)]["hijri"],
               "date": f"{day.day:02d}-{MON[day.month - 1]}-{year}",
               "day": DAYS[day.weekday()]}
        for k in KEYS[1:]:
            va = a[md][k]
            vb = b.get(md, {}).get(k)
            if vb is not None and abs(va - vb) > 2:
                # One of the two years has a copy error here. Prefer the year
                # before when it fits its own neighbouring days: that catches
                # last year's one-day errors and its multi-day blocks (SBH09
                # late March 2026, SBH06 December 2026).
                fa, na = misfit(a, ao, ao.index(md), k)
                fb, _ = misfit(b, bo, bo.index(md), k)
                if fb <= 2:
                    v = vb
                elif fa <= 2:
                    v = va
                else:
                    v = na
                if v != va:
                    fixes.append(f"{row['date']} {k} {hhmm(va)[:5]} -> {hhmm(v)[:5]}")
                va = v
            elif vb is None:
                fa, na = misfit(a, ao, ao.index(md), k)
                if fa > 2:
                    fixes.append(f"{row['date']} {k} {hhmm(va)[:5]} -> {hhmm(na)[:5]}")
                    va = na
            row[k] = hhmm(va)
        row = {kk: row[kk] for kk in ["hijri", "date", "day"]} | {"imsak": hhmm(mins(row["fajr"]) - 10)} | {k: row[k] for k in KEYS[1:]}
        rows.append(row)
        day += timedelta(1)
    assert hijri_rows[len(rows) - 1]["date"] == rows[-1]["date"]
    return rows, fixes


def main():
    """python3 tools/estimate_provisional.py --year 2027 --hijri-from WLY02 SBH01 ... SBH09

    Fetches each zone's two previous years from e-Solat, writes {ZONE}/{YEAR}.json
    marked "provisional": true, and adds the zone to pending.json. Hijri dates
    come from --hijri-from's file for the year (JAKIM's calendar is national).
    """
    import argparse, os, sys
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, root)
    import backup_esolat as b
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--hijri-from", required=True)
    ap.add_argument("zones", nargs="+")
    args = ap.parse_args()
    hijri = json.load(open(os.path.join(root, args.hijri_from, f"{args.year}.json")))["prayerTime"]
    tmp = os.path.join(root, ".estimate_cache")
    os.makedirs(tmp, exist_ok=True)
    pending_path = os.path.join(root, "pending.json")
    pending = json.load(open(pending_path)) if os.path.exists(pending_path) else {}
    for zone in args.zones:
        paths = []
        for y in (args.year - 1, args.year - 2):
            p = os.path.join(tmp, f"{zone}_{y}.json")
            if not os.path.exists(p):
                raw = b.http(b.API.format(zone=zone), {"datestart": f"{y}-01-01", "dateend": f"{y}-12-31"})
                open(p, "wb").write(raw)
            paths.append(p)
        rows, fixes = estimate(args.year, paths[0], paths[1], hijri)
        doc = {"prayerTime": rows, "status": "PROVISIONAL", "provisional": True,
               "note": f"Estimate until JAKIM e-Solat publishes {args.year} for this zone. "
                       f"Built from JAKIM's {args.year - 1} and {args.year - 2} schedules; see README.",
               "periodType": "duration", "lang": "ms_my", "zone": zone}
        raw = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode()
        errs = [e for e in b.validate(raw, zone, args.year) if not e.startswith("status")]
        if errs:
            print(zone, "NOT WRITTEN:", errs)
            continue
        os.makedirs(os.path.join(root, zone), exist_ok=True)
        open(os.path.join(root, zone, f"{args.year}.json"), "wb").write(raw)
        pending.setdefault(str(args.year), {})[zone] = f"Estimate: e-Solat has no {args.year} data yet."
        print(zone, "written,", len(fixes), "copy errors repaired:", "; ".join(fixes[:6]), "..." if len(fixes) > 6 else "")
    with open(pending_path, "w") as fh:
        json.dump(pending, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


if __name__ == "__main__":
    main()
