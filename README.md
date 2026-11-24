# Malaysia Prayer Times Data

Fallback prayer schedules for the Waktu Solat app's Malaysian zones, and the
Selangor district zones JAKIM e-Solat does not serve. Each file is in the same
format as the JAKIM e-Solat `period=year` response.

## Selangor — district zones (from 1 January 2027)

From 2027 Selangor uses nine district-based zones instead of SGR01–SGR03.
Source: official *Takwim Waktu Solat Negeri Selangor 2027 / 1448–1449H*,
Jabatan Mufti Negeri Selangor (https://www.muftiselangor.gov.my/takwim-solat/).
Hijri dates follow JAKIM's national calendar.

`SGRD` codes are this project's own. JAKIM has not published codes for the new
districts yet, so these are kept apart from JAKIM's `SGRnn` codes to avoid clashes.

| Code | District |
|---|---|
| `SGRD01` | Hulu Selangor |
| `SGRD02` | Gombak |
| `SGRD03` | Petaling |
| `SGRD04` | Hulu Langat |
| `SGRD05` | Sepang |
| `SGRD06` | Sabak Bernam |
| `SGRD07` | Kuala Selangor |
| `SGRD08` | Klang |
| `SGRD09` | Kuala Langat |

## JAKIM zones — fallback only

**JAKIM e-Solat is the real source.** The app asks e-Solat first and only uses
these files when e-Solat is down or has nothing for the zone. (Selangor's
districts are the exception: from 2027 this repo is their only source.)

- **JAKIM copies (47):** JHR01–04, KDH01–07, KTN01–02, MLK01, NGS01–03,
  PHG01–07, PLS01, PNG01, PRK01–07, SWK01–09, TRG01–04, WLY01. JAKIM's response
  for 1 Jan – 31 Dec 2027, stored unchanged (fetched 24 Nov 2026).
- **WLY02 (Labuan), corrected copy.** JAKIM's response with two errors fixed;
  nothing else differs.
  - Maghrib 06:28 on 20–25 May 2027 (the same as Dhuha, before Asar) is
    18:28 here. 18:28 is JAKIM's own WLY02 Maghrib for 20–25 May 2023, the
    year with the same leap-year position (2023 and 2027 Maghrib agree on 354
    of the other 359 days), and fits 19 May (18:28) and 26 May (18:29).
  - Asar 14:50 on 10 Jan 2027 is 15:50 here: JAKIM has 15:50 on 10 January in
    2023, 2024, 2025 and 2026, and 15:50 on 9 and 11 January 2027.
- **SBH01–SBH09 (Sabah), estimates.** e-Solat has no Sabah 2027 yet (checked
  24 Nov 2026; Pejabat Mufti Negeri Sabah's site points to e-Solat and has no
  2027 PDF). These files are **not JAKIM's timetable**: they say
  `"provisional": true` and `"status": "PROVISIONAL"`, and are replaced by
  JAKIM's own as soon as it is published. See below for how they are made.
- SGR01–SGR03: replaced by the Selangor district zones above.

### How the Sabah estimates are made

`tools/estimate_provisional.py`:
- **Each time** is JAKIM's 2026 time for the same date.
- **Where 2026 and 2025 differ by more than 2 minutes,** one of them has a
  copy error. The 2025 value is used if it fits its own neighbouring days;
  otherwise the 2026 value if it does; otherwise the median of the 2026
  neighbours. This repaired:
  - SBH06, 12–14 March: a 3-day block 3–6 minutes off.
  - SBH06, December: Maghrib about 9 minutes earlier all month than both 2025
    and January–November 2026. 2026's December matches the zone's pre-2025
    times, so it looks like old data. The 2025 (current) times are used, which
    is also the later, safer side for Maghrib.
  - SBH09, 28–31 March: a 4-day block about 10 minutes off.
- **Imsak** is Subuh less 10 minutes, as in every JAKIM row except copy errors.
- **Hijri dates** come from JAKIM's national 2027 calendar (the same in every
  zone).
- **Accuracy:** the same method, tried on six zones whose real 2027 is known
  (WLY02, SWK01, SWK08, KTN01, JHR01, PRK02), was exact on 93.4% of
  times and within 1 minute on all of them, Dhuha aside. JHR01's Dhuha
  changed by 2 minutes in 2027. On Sabah itself, 2026 estimated from
  2025 + 2024 matched JAKIM's 2026 to within 1 minute on 99.2% of times; most
  of the rest are JAKIM's own 2026 errors.

## Daily check until JAKIM is right

`pending.json` lists every zone whose file here is not JAKIM's own (the
estimates and the corrected copy). Check it **every day** until it is empty:

```sh
python3 backup_esolat.py --year 2027 --pending
```

- **Nothing changes until JAKIM is right.** "no data" means e-Solat still has
  nothing. "INVALID" means JAKIM's file still has an error (a day whose times
  go backwards, or a time more than 3 minutes off the days on both sides).
  Neither changes anything here.
- **When JAKIM's answer passes,** it replaces our file byte for byte and the
  zone leaves `pending.json`. Commit, push, and purge jsDelivr:
  `https://purge.jsdelivr.net/gh/waktu-solat/malaysia@main/{ZONE}/2027.json`.
- **The app picks it up without an update.** Phones that stored an estimate
  try e-Solat again once a day.

## Structure
```text
.
├── SGRD01 … SGRD09/        Selangor districts (Jabatan Mufti Negeri Selangor)
│   └── 2027.json
├── JHR01 … WLY02/         JAKIM e-Solat fallback copies
│   └── 2027.json
├── SBH01 … SBH09/         provisional estimates (until JAKIM publishes)
│   └── 2027.json
├── pending.json           zones still waiting for a correct JAKIM file
├── backup_esolat.py       fetch, validate and store JAKIM's files
└── tools/estimate_provisional.py
```

## CDN Endpoint
Served via jsDelivr:
`https://cdn.jsdelivr.net/gh/waktu-solat/malaysia@main/{ZONE}/{YEAR}.json`

Keep the repo well under jsDelivr's 50 MB GitHub package limit.
