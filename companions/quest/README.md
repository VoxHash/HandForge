# HandForge Meta Quest 3 companion

Quest-friendly remote queue monitor and shared control for a desktop HandForge instance. Heavy on-headset encodes are **out of scope** for this phase — the headset talks to the LAN Orchestrator API.

## What ships

| Piece | Location |
| --- | --- |
| Quest UI (large hit targets, simplified layout) | Served at `/quest.html` from `handforge/companion/static/quest.html` |
| Phone / PWA UI | `/` (`index.html`) |
| This guide | `companions/quest/README.md` |

## Use on Quest 3 (Browser)

1. On the desktop (same LAN):  
   `python -m handforge serve --lan`  
   Note the printed URL (`http://<lan-ip>:8765/?token=…`).
2. In **Quest Browser**, open that URL, then switch to the Quest layout:  
   `http://<lan-ip>:8765/quest.html?token=…`  
   (or tap **Quest UI** on the phone companion page).
3. Optional: use Browser’s **Add to Home** / install affordance with the companion Web App Manifest for a 2D panel shortcut.

The UI polls `GET /api/status` every second and drives `POST /api/control/*` with the shared token (same security model as the phone companion).

## Packaging notes (Meta Horizon / Bubblewrap)

Meta documents packaging a **2D PWA** for Horizon OS via Bubblewrap (`bubblewrap init --manifest=… --metaquest`). That path needs a **public HTTPS origin** and Digital Asset Links — not appropriate for a localhost/LAN-only companion.

For HandForge:

- **Supported now**: Quest Browser → LAN companion URL (HTTP + token).
- **Later (store)**: host a TLS reverse proxy to your workstation or a relay; then Bubblewrap 2D mode against that origin. Immersive WebXR is unnecessary for queue control.

## Short media prep

Trim/export from the headset remains a stretch goal. Use host paths via shared control (**Add to pending** with absolute paths the desktop can read), Start/Stop, and real-time preview (`POST /api/control/preview`) from the phone UI when you need a clip check.

## Related

- [docs/companions.md](../../docs/companions.md)
- Android / GrapheneOS shell: [../android/README.md](../android/README.md)
