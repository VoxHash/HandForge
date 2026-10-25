# Bundled FFmpeg (`libffmpeg.so`)

Prebuilt binaries are **not** committed (large + LGPL redistributable). Fetch them:

```bash
./scripts/fetch-android-ffmpeg.sh
# optional emulator ABI:
./scripts/fetch-android-ffmpeg.sh --with-x86_64
```

Then build the APK (`./gradlew assembleDebug`). Termux remains the fallback when these files are absent.
