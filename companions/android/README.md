# HandForge Android / GrapheneOS companion

Privacy-first shell for the HandForge companion Orchestrator API. Targets **sideload / F-Droid-style** installs — **no Google Play Services**, Firebase, or Ads SDKs.

Two delivery paths ship in this folder:

1. **PWA** — install the companion page from Vanadium / Chrome (“Add to Home Screen”) while `handforge serve --lan` is running on the desktop.
2. **Native WebView APK** — Gradle project under `android/` that opens a connect screen, then loads the live companion UI over LAN HTTP.

Optional **Capacitor** metadata (`package.json`, `capacitor.config.json`, `www/`) is included so you can wrap the same connector page with `@capacitor/android` when Node is available. Capacitor is not required to build the WebView APK.

## GrapheneOS notes

- Uses the system **Vanadium WebView** (no Google WebView package dependency).
- Cleartext HTTP is allowed **only** for RFC1918 LAN hosts so you can reach `http://192.168.x.x:8765` without TLS.
- Distribution: `adb install` or F-Droid-style APK; Play Store is out of scope for this scaffold.

On-device FFmpeg encode is **deferred** (needs a bundled or Termux FFmpeg + storage UX). This client remote-controls the desktop Orchestrator.

## Prerequisites

- Desktop: HandForge with companion enabled (`handforge serve --lan` or Preferences → Companion on `0.0.0.0` + token).
- Phone: Android 8+ / GrapheneOS; same LAN as the host.
- Build: Android Studio Hedgehog+ **or** **JDK 17 or 21** + Android SDK (`ANDROID_HOME`). AGP does not accept some distro OpenJDK 27 version strings (e.g. Arch `27.0.1.0.2`); point `JAVA_HOME` at Temurin/OpenJDK 17 before `./gradlew`.

## Build the WebView APK

```bash
cd companions/android/android
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Open the app → enter host (e.g. `192.168.1.20`), port `8765`, paste the companion token → **Connect**.

## PWA install (no APK)

1. On the phone browser open the printed companion URL (`?token=…`).
2. Vanadium / Chrome → **Install app** / **Add to Home Screen**.
3. Optional Quest-sized UI: `/quest.html?token=…`.

## Capacitor wrap (optional)

```bash
cd companions/android
npm install
npx cap add android   # if not using the bundled android/ WebView project
npx cap sync
npx cap open android
```

`capacitor.config.json` points `webDir` at `www/` (local connector). For production you normally still navigate to the LAN companion origin after connect so APIs stay same-origin with the host token.

## API surface used

- `GET /api/health`, `GET /api/status`
- `GET|POST /api/control/*` (token required for writes)
- `POST /api/control/preview`, `GET /api/preview/{id}`
- `GET /api/presets`, `POST /api/presets/import`
- `GET /api/analytics/report`

See [docs/companions.md](../../docs/companions.md).
