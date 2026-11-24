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

## Structure
```text
.
└── SGRD01 … SGRD09/
    └── 2027.json
```

## CDN Endpoint
Served via jsDelivr:
`https://cdn.jsdelivr.net/gh/waktu-solat/malaysia@main/{ZONE}/{YEAR}.json`

Keep the repo well under jsDelivr's 50 MB GitHub package limit.
