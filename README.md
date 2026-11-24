# Malaysia Prayer Times Data

Prayer schedules for Malaysian zones that JAKIM e-Solat does not (yet) serve.
Each file is in the same format as the JAKIM e-Solat `period=year` response.

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

## JAKIM zones — backup copy

A copy of JAKIM e-Solat's 2027 schedule for every other zone, for when e-Solat
is unavailable. Each file is JAKIM's response for 1 Jan – 31 Dec 2027, stored
unchanged (fetched 24 Nov 2026), except for the WLY02 correction below.

- **Included (48):** JHR01–04, KDH01–07, KTN01–02, MLK01, NGS01–03, PHG01–07,
  PLS01, PNG01, PRK01–07, SWK01–09, TRG01–04, WLY01–02.
- **WLY02 (Labuan) correction:** JAKIM's 2027 data gives Maghrib as 06:28 on
  20–25 May 2027, before Subuh's end and the same as Dhuha. This copy has
  18:28 on those six days; nothing else differs from JAKIM's response. 18:28 is
  JAKIM's own WLY02 Maghrib for 20–25 May 2023, the year with the same
  leap-year position (2023 and 2027 Maghrib agree on 354 of the other 359
  days), and fits 19 May (18:28) and 26 May (18:29) of 2027.
- **Not included yet:**
  - SBH01–SBH09 (Sabah): JAKIM has no 2027 data yet (checked 24 Nov 2026;
    Pejabat Mufti Negeri Sabah's site points to e-Solat and has no 2027 PDF).
  - SGR01–SGR03: replaced by the Selangor district zones above.

## Structure
```text
.
├── SGRD01 … SGRD09/   Selangor districts (Jabatan Mufti Negeri Selangor)
│   └── 2027.json
└── JHR01 … WLY01/     JAKIM e-Solat backup
    └── 2027.json
```

## CDN Endpoint
Served via jsDelivr:
`https://cdn.jsdelivr.net/gh/waktu-solat/malaysia@main/{ZONE}/{YEAR}.json`

Keep the repo well under jsDelivr's 50 MB GitHub package limit.
