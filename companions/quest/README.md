# HandForge Meta Quest 3 companion

Quest-friendly remote queue monitor and shared control for a desktop HandForge instance. Heavy on-headset encodes are **out of scope** for this phase — the headset talks to the LAN Orchestrator API (or a TLS origin for store packaging).

## What ships

| Piece | Location |
| --- | --- |
| Quest UI (large hit targets, simplified layout) | Served at `/quest.html` from `handforge/companion/static/quest.html` |
| Phone / PWA UI | `/` (`index.html`) |
| Quest store web manifest | `/quest.webmanifest` (`start_url`: `/quest.html`) |
| HTTPS / Bubblewrap kit | [`bubblewrap/`](bubblewrap/) + [`scripts/quest-https-package.sh`](../../scripts/quest-https-package.sh) |
| This guide | `companions/quest/README.md` |

## Use on Quest 3 (Browser — supported now)

1. On the desktop (same LAN):  
   `python -m handforge serve --lan`  
   Note the printed URL (`http://<lan-ip>:8765/?token=…`).
2. In **Quest Browser**, open that URL, then switch to the Quest layout:  
   `http://<lan-ip>:8765/quest.html?token=…`  
   (or tap **Quest UI** on the phone companion page).
3. Optional: use Browser’s **Add to Home** / install affordance with the companion Web App Manifest for a 2D panel shortcut.

The UI prefers `GET /api/events` (SSE) and falls back to polling `GET /api/status`; control uses `POST /api/control/*` with the shared token.

## Packaging (Meta Horizon / Bubblewrap — HTTPS)

Store / sideload TWA packaging needs a **public HTTPS origin** and Digital Asset Links. Full kit:

- Guide: [bubblewrap/README.md](bubblewrap/README.md)
- Walkthrough: [docs/examples/example-03.md](../../docs/examples/example-03.md)
- Script: `./scripts/quest-https-package.sh doctor`

Summary:

1. Reverse-proxy TLS to local `handforge serve` (see `bubblewrap/Caddyfile.example`).
2. `configure` + `publish-assetlinks` so `https://<host>/.well-known/assetlinks.json` is live.
3. `bubblewrap` build (`horizonOSAppMode: 2D`) → `adb install` the signed APK.

Immersive WebXR is unnecessary for queue control.

## Short media prep

Trim/export from the headset remains a stretch goal. Use host paths via shared control (**Add to pending** with absolute paths the desktop can read), Start/Stop, and real-time preview (`POST /api/control/preview`) from the phone UI when you need a clip check.

## Related

- [docs/companions.md](../../docs/companions.md)
- Android / GrapheneOS shell: [../android/README.md](../android/README.md)
