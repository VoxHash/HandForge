# Companions — Android / GrapheneOS, Meta Quest 3, PWA

HandForge companions remote-control a **desktop Orchestrator** over the LAN. They do not replace the PyQt6 desktop app. The Android APK also supports **on-device encode** via Termux FFmpeg (or optional bundled `libffmpeg.so`).

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
| Quest / Horizon store (HTTPS) | Public TLS origin + Bubblewrap 2D TWA — [companions/quest/bubblewrap/](../companions/quest/bubblewrap/) · `scripts/quest-https-package.sh` · [example-03](examples/example-03.md) |
| Android / GrapheneOS APK | Build [companions/android/android](../companions/android/android) — no Play Services — see [companions/android/README.md](../companions/android/README.md) |
| Capacitor wrap (optional) | `companions/android/` `package.json` + `www/` connector |

## On-device Android encode

In the APK: **On-device encode** → SAF pick → stage under `Download/HandForge/` → run FFmpeg.

- Presets: `companions/android/android/app/src/main/assets/encode_presets.json` (validated by `tests/test_ondevice_presets.py` against host FFmpeg).
- Termux: `pkg install ffmpeg`, `allow-external-apps = true`, grant `com.termux.permission.RUN_COMMAND`.
- Optional: drop ABI-specific `libffmpeg.so` into `jniLibs` for a Termux-free backend.
- CI: `.github/workflows/android-companion.yml` (Temurin JDK 17 `assembleDebug` + unit tests).

## Advanced companion APIs

| Endpoint | Purpose |
| --- | --- |
| `GET /api/events` | Live status via Server-Sent Events (same token auth as `/api/status`; UIs fall back to 1s polling) |
| `POST /api/control/preview` | Real FFmpeg short clip / thumbnail (`path` or active `wid`) |
| `GET /api/preview/{id}` | Fetch generated preview bytes |
| `GET /api/presets` / `export` | List / export custom presets for LAN sharing |
| `POST /api/presets/import` | Import shared preset JSON (token required) |
| `GET /api/analytics/report` | Advanced local-only aggregate analytics |

## Crash-safe queue

Unfinished pending/queued/active jobs are persisted to `~/.handforge/queue.json` (atomic replace). The desktop GUI and `handforge serve` restore existing media paths on startup. Clearing the queue or finishing with an empty work set removes the file.

## Quest HTTPS / Bubblewrap

For Horizon Store or sideload TWA packaging (not required for LAN Browser):

1. Terminate TLS in front of `handforge serve` (`companions/quest/bubblewrap/Caddyfile.example`).
2. Publish Digital Asset Links: `./scripts/quest-https-package.sh configure && … publish-assetlinks`.
3. Confirm `https://<host>/quest.webmanifest` and `https://<host>/.well-known/assetlinks.json`.
4. Build with Meta `@meta-quest/bubblewrap-cli` (`horizonOSAppMode: 2D`).

Details: [companions/quest/bubblewrap/README.md](../companions/quest/bubblewrap/README.md).

## Privacy

- Opt-in; default bind localhost.
- LAN binds require a shared token; **all control writes require a token**.
- A public HTTPS origin for store packaging exposes the companion — use a strong token and preferably VPN / IP allowlists at the reverse proxy.
- GrapheneOS path assumes **Vanadium WebView** and sideload — no Google Play Services.
- On-device encodes stay on the phone (Download/HandForge + Termux); nothing is uploaded.
