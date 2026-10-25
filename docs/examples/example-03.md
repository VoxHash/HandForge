# Example 3: Quest / store HTTPS packaging (Bubblewrap)

Build a Meta Horizon **2D** APK that wraps the HandForge Quest companion PWA against a public TLS origin.

## Goal

Sideload (or later submit) a Trusted Web Activity that opens `https://<your-host>/quest.html` with Digital Asset Links verification — without replacing the supported LAN Browser path.

## Steps

1. Start the companion on the workstation:

   ```bash
   python -m handforge serve --lan
   ```

2. Terminate TLS in front of it (edit the hostname first):

   ```bash
   # companions/quest/bubblewrap/Caddyfile.example
   caddy run --config companions/quest/bubblewrap/Caddyfile.example
   ```

3. Install the Meta Bubblewrap CLI and configure packaging:

   ```bash
   ./scripts/quest-https-package.sh install-cli
   export HANDFORGE_HTTPS_HOST=companion.example.com
   # After creating a keystore, copy SHA-256 from:
   ./scripts/quest-https-package.sh fingerprint
   export HANDFORGE_SHA256_FINGERPRINT='AA:BB:…'
   ./scripts/quest-https-package.sh configure
   ./scripts/quest-https-package.sh publish-assetlinks
   ```

4. Confirm the origin (must be real HTTPS DNS, not localhost):

   ```bash
   ./scripts/quest-https-package.sh verify-origin
   # Expect JSON for /quest.webmanifest and /.well-known/assetlinks.json
   ```

5. Build and sideload:

   ```bash
   export BUBBLEWRAP_KEYSTORE_PASSWORD=…
   export BUBBLEWRAP_KEY_PASSWORD=…
   ./scripts/quest-https-package.sh build
   adb install companions/quest/bubblewrap/project/app-release-signed.apk
   ```

6. On Quest, open the app from **Unknown Sources**, enter the companion token when prompted (same as LAN).

## Notes

- `horizonOSAppMode` is **`2D`** (queue UI is not WebXR).
- Keep the keystore offline and backed up; Store updates must reuse it.
- Full reference: [companions/quest/bubblewrap/README.md](../../companions/quest/bubblewrap/README.md).
