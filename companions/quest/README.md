# HandForge Meta Quest 3 companion

Quest-friendly remote queue monitor, shared control, and **on-headset encode** via the Android companion APK (Quest runs Android / Horizon OS).

## What ships

| Piece | Location |
| --- | --- |
| Quest UI (large hit targets, simplified layout) | Served at `/quest.html` from `handforge/companion/static/quest.html` |
| Phone / PWA UI | `/` (`index.html`) |
| Quest store web manifest | `/quest.webmanifest` (`start_url`: `/quest.html`) |
| HTTPS / Bubblewrap kit | [`bubblewrap/`](bubblewrap/) + [`scripts/quest-https-package.sh`](../../scripts/quest-https-package.sh) |
| On-headset FFmpeg | Same Android APK: [`../android/`](../android/) → `LocalEncodeActivity` + heavy presets |
| This guide | `companions/quest/README.md` |

## Use on Quest 3 (Browser — LAN host)

1. On the desktop (same LAN):  
   `python -m handforge serve --lan`  
   Note the printed URL (`http://<lan-ip>:8765/?token=…`).
2. In **Quest Browser**, open that URL, then switch to the Quest layout:  
   `http://<lan-ip>:8765/quest.html?token=…`  
   (or tap **Quest UI** on the phone companion page).
3. Optional: use Browser’s **Add to Home** / install affordance with the companion Web App Manifest for a 2D panel shortcut.

The UI prefers `GET /api/events` (SSE) and falls back to polling `GET /api/status`; control uses `POST /api/control/*` with the shared token.

**Quest Browser alone cannot run local FFmpeg.** Use Shared control to enqueue host paths, or sideload the APK below for on-headset encodes.

## On-headset heavy encodes (Android APK on Quest)

Quest is Android-based. There is **no separate Quest FFmpeg stack** — reuse the GrapheneOS / Android companion:

1. Developer Mode on the headset + USB debugging ([Meta device setup](https://developers.meta.com/horizon/documentation/native/android/mobile-device-setup/)).
2. From the repo (host PC):
   ```bash
   ./scripts/fetch-android-ffmpeg.sh          # optional but recommended — bundled libffmpeg.so
   cd companions/android/android
   ./gradlew assembleDebug
   adb install -r app/build/outputs/apk/debug/app-debug.apk
   ```
3. On Quest: open **HandForge** → **On-headset encode** (or Connect → Quest UI).  
   Inside `/quest.html` loaded by the APK WebView, **Open on-headset encode** / **Heavy presets only** call `HandForgeNative` → `LocalEncodeActivity`.
4. Pick capture media (SAF) → stage under `Download/HandForge/` → encode with a **Heavy** preset (`video_mp4_quest_720_hq`, `video_mp4_quest_1080`, `video_mp4_quest_bitrate`, high-bitrate audio).

**Termux on Quest (optional fallback):** sideload Termux, `pkg install ffmpeg`, `allow-external-apps = true`, grant `RUN_COMMAND`. Bundled `libffmpeg.so` is preferred when present.

### Thermal / performance (honest limits)

- Quest XR2 Gen 2 is **passively cooled**. Sustained software encodes draw meaningful power (~2.5–3 W class for video encode) and often **throttle after roughly 5–15 minutes**.
- Heavy presets use `-threads 2` and `veryfast` / `ultrafast` to reduce sustained load. Prefer **720p HQ** for longer clips.
- **LAN host Orchestrator remains primary** for long recordings, batches, and 2-pass / high-CRF desktop quality. Use Shared control on `/quest.html` for those jobs.

Presets live in `companions/android/android/app/src/main/assets/encode_presets.json` (`tier: "heavy"`).

## Packaging (Meta Horizon / Bubblewrap — HTTPS)

Store / sideload TWA packaging needs a **public HTTPS origin** and Digital Asset Links. Full kit:

- Guide: [bubblewrap/README.md](bubblewrap/README.md)
- Walkthrough: [docs/examples/example-03.md](../../docs/examples/example-03.md)
- Script: `./scripts/quest-https-package.sh doctor`

Summary:

1. Reverse-proxy TLS to local `handforge serve` (see `bubblewrap/Caddyfile.example`).
2. `configure` + `publish-assetlinks` so `https://<host>/.well-known/assetlinks.json` is live.
3. `bubblewrap` build (`horizonOSAppMode: 2D`) → `adb install` the signed APK.

Immersive WebXR is unnecessary for queue control. Bubblewrap TWA wraps the web UI only — on-headset FFmpeg still needs the HandForge Android companion APK (or Termux).

## Related

- [docs/companions.md](../../docs/companions.md)
- Android / GrapheneOS shell: [../android/README.md](../android/README.md)
