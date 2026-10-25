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

## On-device FFmpeg encode

The APK includes **On-device encode** (beside Connect / Quest UI):

1. Pick audio/video via the system document picker (SAF).
2. Media is staged under shared `Download/HandForge/` so Termux can read it.
3. Encode runs with curated presets from `android/app/src/main/assets/encode_presets.json` (MP3 / AAC / Opus / MP4 H.264).

**Backends (first match wins):**

| Backend | Requirement |
| --- | --- |
| Bundled `libffmpeg.so` | Run `./scripts/fetch-android-ffmpeg.sh` (pins husen-hn FFmpeg 7.1 zips for `armeabi-v7a` + `arm64-v8a`; optional `--with-x86_64`). Installs CLI as `jniLibs/<abi>/libffmpeg.so` plus `libav*` / `libsw*` deps. Blobs are gitignored (~15–16 MB/ABI). APK uses `extractNativeLibs=true` + `LD_LIBRARY_PATH`. |
| Termux | Install [Termux](https://termux.dev), `pkg install ffmpeg`, set `allow-external-apps = true` in `~/.termux/termux.properties`, grant **RUN_COMMAND** to HandForge |

Remote desktop Orchestrator control remains the primary path; on-device encode is for short local jobs without a PC.

### Meta Quest (on-headset)

Quest runs Android. Sideload this same APK (`adb install` with Developer Mode). On Quest the Connect screen shows **On-headset encode**, which opens `LocalEncodeActivity` with **heavy** presets first (1080p / 720p HQ / high-bitrate audio). `/quest.html` inside the WebView exposes `HandForgeNative.openLocalEncode` / `openHeavyEncode`. See [companions/quest/README.md](../quest/README.md) for thermal limits — LAN host encode stays primary for huge jobs.

### Termux-free APK (bundled FFmpeg)

```bash
# From repo root — downloads + SHA256-verifies prebuilts into jniLibs (not committed)
./scripts/fetch-android-ffmpeg.sh
# optional: ./scripts/fetch-android-ffmpeg.sh --with-x86_64
./scripts/fetch-android-ffmpeg.sh --check   # verify layout

export JAVA_HOME=/path/to/temurin-17
cd companions/android/android
./gradlew assembleDebug
# APK embeds libffmpeg.so for fetched ABIs; On-device encode prefers bundled over Termux
```

Default CI builds **without** fetching blobs (Termux-only path still compiles). Manual workflow dispatch can set **fetch_bundled_ffmpeg** to true.

## Prerequisites

- Desktop: HandForge with companion enabled (`handforge serve --lan` or Preferences → Companion on `0.0.0.0` + token).
- Phone: Android 8+ / GrapheneOS; same LAN as the host (for remote control).
- Build: Android Studio Hedgehog+ **or** **JDK 17 or 21 (Temurin)** + Android SDK (`ANDROID_HOME`). AGP rejects some distro OpenJDK 27 version strings (e.g. Arch `27.0.1.0.2`); point `JAVA_HOME` at Temurin/OpenJDK 17 before `./gradlew`.

CI builds the debug APK with Temurin 17 (`.github/workflows/android-companion.yml`).

## Build the WebView APK

```bash
# Use JDK 17 — required for Android Gradle Plugin
export JAVA_HOME=/path/to/temurin-17   # e.g. /usr/lib/jvm/java-17-openjdk
cd companions/android/android
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

Unit tests for preset parsing / argv:

```bash
./gradlew testDebugUnitTest
```

Open the app → **Connect** for LAN control, or **On-device encode** for Termux/local FFmpeg.

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

## API surface used (remote control)

- `GET /api/health`, `GET /api/status`, `GET /api/events`
- `GET|POST /api/control/*` (token required for writes)
- `POST /api/control/preview`, `GET /api/preview/{id}`
- `GET /api/presets`, `POST /api/presets/import`
- `GET /api/analytics/report`

See [docs/companions.md](../../docs/companions.md).
