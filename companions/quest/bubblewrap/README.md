# Quest / store HTTPS packaging (Bubblewrap)

Package the HandForge companion as a **Meta Horizon 2D PWA** (Trusted Web Activity) with [`@meta-quest/bubblewrap-cli`](https://www.npmjs.com/package/@meta-quest/bubblewrap-cli).

LAN HTTP in Quest Browser remains the day-to-day path. This kit is for a **public HTTPS origin** + Digital Asset Links so Horizon / sideload TWA verification succeeds.

Canonical Meta guide: [Package a PWA for Meta Quest](https://developers.meta.com/horizon/documentation/web/pwa-packaging/).

## What ships here

| File | Purpose |
| --- | --- |
| `twa-manifest.template.json` | Scripted Bubblewrap project (`horizonOSAppMode`: **`2D`**, start `/quest.html`) |
| `assetlinks.template.json` | Digital Asset Links template (package + SHA-256 fingerprint) |
| `Caddyfile.example` / `nginx.conf.example` | TLS reverse proxy → local `handforge serve` |
| `../../../../scripts/quest-https-package.sh` | configure / publish-assetlinks / build / verify |
| Companion `quest.webmanifest` | Store-oriented web manifest (`start_url`: `/quest.html`) |
| Companion `GET /.well-known/assetlinks.json` | Unauthenticated DAL file once published into static |

Default Android package id: `dev.voxhash.handforge.quest`.

## Prerequisites

1. **Public HTTPS hostname** pointing at a reverse proxy that forwards to HandForge companion (`127.0.0.1:8765` or your bind).
2. Node.js **18+** and `npm`.
3. Signing keystore (create once; **back it up** — Store updates must reuse the same cert).
4. Developer-mode Quest + `adb` for sideload testing.

Horizon Application ID / billing is optional for this 2D queue UI (no IAP). Use `applicationId` `"0"` until you register a Store app.

## Quick path (scripted)

```bash
# 1) TLS in front of companion (edit hostnames first)
#    companions/quest/bubblewrap/Caddyfile.example

# 2) Install Meta Bubblewrap CLI
./scripts/quest-https-package.sh install-cli

# 3) Create a keystore (example — pick your own passwords; do not commit)
mkdir -p companions/quest/bubblewrap/project
keytool -genkeypair -v \
  -keystore companions/quest/bubblewrap/project/android.keystore \
  -alias android -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=HandForge Quest, OU=VoxHash, O=VoxHash Technologies, C=US"

# 4) Read SHA-256 fingerprint
./scripts/quest-https-package.sh fingerprint
# or: keytool -list -v -keystore … -alias android | grep SHA256

# 5) Render manifests + publish DAL into the companion package
export HANDFORGE_HTTPS_HOST=companion.example.com
export HANDFORGE_SHA256_FINGERPRINT='AA:BB:CC:…'
./scripts/quest-https-package.sh configure
./scripts/quest-https-package.sh publish-assetlinks
# Restart / redeploy so https://companion.example.com/.well-known/assetlinks.json serves

# 6) Confirm origin
./scripts/quest-https-package.sh verify-origin

# 7) Build signed APK / AAB
export BUBBLEWRAP_KEYSTORE_PASSWORD=…
export BUBBLEWRAP_KEY_PASSWORD=…
./scripts/quest-https-package.sh build

# 8) Sideload
adb install companions/quest/bubblewrap/project/app-release-signed.apk
```

Interactive alternative (TTY required):

```bash
mkdir -p companions/quest/bubblewrap/project && cd companions/quest/bubblewrap/project
bubblewrap init --manifest=https://companion.example.com/quest.webmanifest --metaquest
# Choose App mode: 2D · display: standalone · orientation: landscape
bubblewrap fingerprint add '<SHA256>'
# Host generated assetlinks.json at /.well-known/assetlinks.json
bubblewrap build
```

## Digital Asset Links

Browsers verify `https://<host>/.well-known/assetlinks.json` against the **signing** certificate of the APK the headset actually runs.

- After `publish-assetlinks`, HandForge serves the file from `handforge/companion/static/.well-known/assetlinks.json` **without** a companion token (required for automated verification).
- Include both upload and Play/Horizon app-signing fingerprints if they differ (`bubblewrap fingerprint add` multiple times).
- Until a real fingerprint is published, only the `.example` file is in git — copy via the script.

## Security notes

- Store packaging exposes the companion on the public internet. Keep a strong `companion_token`; prefer IP allowlists / VPN / mutual TLS at the reverse proxy when possible.
- Control writes always require the token.
- Do **not** commit keystores, APKs, or live `assetlinks.json` with production fingerprints into the repo (`project/` and `generated/` are gitignored).

## Related

- [companions/quest/README.md](../README.md) — Quest Browser LAN usage
- [docs/companions.md](../../../docs/companions.md)
- [docs/examples/example-03.md](../../../docs/examples/example-03.md) — end-to-end HTTPS packaging example
