# Companions — Android / GrapheneOS, Meta Quest 3, PWA

HandForge companions remote-control a **desktop Orchestrator** over the LAN. They do not replace the PyQt6 desktop app.

## Host setup

```bash
python -m handforge serve --lan
# or enable Preferences → Advanced → Companion (bind 0.0.0.0 + token)
```

Open the printed URL (`?token=…`) on a phone, Quest Browser, or the Android WebView shell.

## Surfaces

| Client | How to run |
| --- | --- |
| Phone / desktop browser | `http://<host>:8765/?token=…` |
| PWA install | Same URL → browser **Install** / Add to Home Screen (`manifest.webmanifest` + `sw.js`) |
| Quest 3 (large UI) | `http://<host>:8765/quest.html?token=…` — see [companions/quest/README.md](../companions/quest/README.md) |
| Android / GrapheneOS APK | Build [companions/android/android](../companions/android/android) — no Play Services — see [companions/android/README.md](../companions/android/README.md) |
| Capacitor wrap (optional) | `companions/android/` `package.json` + `www/` connector |

## Advanced companion APIs

| Endpoint | Purpose |
| --- | --- |
| `POST /api/control/preview` | Real FFmpeg short clip / thumbnail (`path` or active `wid`) |
| `GET /api/preview/{id}` | Fetch generated preview bytes |
| `GET /api/presets` / `export` | List / export custom presets for LAN sharing |
| `POST /api/presets/import` | Import shared preset JSON (token required) |
| `GET /api/analytics/report` | Advanced local-only aggregate analytics |

## Privacy

- Opt-in; default bind localhost.
- LAN binds require a shared token; **all control writes require a token**.
- GrapheneOS path assumes **Vanadium WebView** and sideload — no Google Play Services.
- On-device FFmpeg encode on phone/headset is deferred (remote control ships first).
