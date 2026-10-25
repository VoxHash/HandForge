#!/usr/bin/env bash
# HandForge — Quest / Horizon store HTTPS packaging helper (Bubblewrap TWA).
#
# Packages the companion PWA against a public TLS origin for Meta Quest 2D
# (horizonOSAppMode=2D). LAN HTTP remains supported without this path.
#
# Usage:
#   ./scripts/quest-https-package.sh help
#   HANDFORGE_HTTPS_HOST=companion.example.com \
#     HANDFORGE_SHA256_FINGERPRINT='AA:BB:...' \
#     ./scripts/quest-https-package.sh configure
#   ./scripts/quest-https-package.sh publish-assetlinks
#   ./scripts/quest-https-package.sh build
#
# Docs: companions/quest/bubblewrap/README.md
# Meta: https://developers.meta.com/horizon/documentation/web/pwa-packaging/

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BW_DIR="${ROOT}/companions/quest/bubblewrap"
PROJECT_DIR="${BW_DIR}/project"
GENERATED_DIR="${BW_DIR}/generated"
STATIC_WELL_KNOWN="${ROOT}/handforge/companion/static/.well-known"

PACKAGE_ID="${HANDFORGE_PACKAGE_ID:-dev.voxhash.handforge.quest}"
KEYSTORE_ALIAS="${HANDFORGE_KEYSTORE_ALIAS:-android}"
KEYSTORE_PATH="${HANDFORGE_KEYSTORE_PATH:-${PROJECT_DIR}/android.keystore}"
HOST="${HANDFORGE_HTTPS_HOST:-}"
FINGERPRINT="${HANDFORGE_SHA256_FINGERPRINT:-}"
BUBBLEWRAP_PKG="${HANDFORGE_BUBBLEWRAP_PKG:-@meta-quest/bubblewrap-cli}"

die() { echo "error: $*" >&2; exit 1; }

need_host() {
  [[ -n "${HOST}" ]] || die "set HANDFORGE_HTTPS_HOST to your public TLS hostname (no scheme), e.g. companion.example.com"
  [[ "${HOST}" != *"://"* ]] || die "HANDFORGE_HTTPS_HOST must be a hostname only (no https://)"
  [[ "${HOST}" != *"/"* ]] || die "HANDFORGE_HTTPS_HOST must not include a path"
}

normalize_fingerprint() {
  local raw="$1"
  raw="$(echo "${raw}" | tr '[:lower:]' '[:upper:]' | tr -d '[:space:]')"
  if [[ "${raw}" != *:* ]]; then
    # Insert colons every two hex chars if caller passed contiguous hex
    local out="" i
    for ((i = 0; i < ${#raw}; i += 2)); do
      [[ -n "${out}" ]] && out+=":"
      out+="${raw:i:2}"
    done
    raw="${out}"
  fi
  echo "${raw}"
}

cmd_help() {
  cat <<'EOF'
HandForge Quest / store HTTPS packaging

Commands:
  help                 Show this help
  check                Verify Node / bubblewrap / openssl availability
  install-cli          npm install -g @meta-quest/bubblewrap-cli
  configure            Render twa-manifest.json + assetlinks.json into generated/
  publish-assetlinks   Copy assetlinks.json into companion static /.well-known/
  fingerprint          Print SHA-256 of HANDFORGE_KEYSTORE_PATH (needs keytool)
  build                bubblewrap update + build in companions/quest/bubblewrap/project/
  verify-origin        HTTPS GET manifest + assetlinks on HANDFORGE_HTTPS_HOST
  doctor               check + summarize next manual steps

Environment:
  HANDFORGE_HTTPS_HOST              Public hostname (required for configure/verify)
  HANDFORGE_SHA256_FINGERPRINT      Signing cert SHA-256 (colon-hex or contiguous)
  HANDFORGE_PACKAGE_ID              Android package (default: dev.voxhash.handforge.quest)
  HANDFORGE_KEYSTORE_PATH           Keystore path (default: project/android.keystore)
  HANDFORGE_KEYSTORE_ALIAS          Key alias (default: android)
  BUBBLEWRAP_KEYSTORE_PASSWORD      For non-interactive bubblewrap build
  BUBBLEWRAP_KEY_PASSWORD           For non-interactive bubblewrap build

Typical flow:
  1. Put companion behind TLS (see Caddyfile.example / nginx.conf.example)
  2. Create / reuse a signing keystore (keep outside web roots; back it up)
  3. configure → publish-assetlinks → deploy static assetlinks on the origin
  4. build → adb install app-release-signed.apk on a developer-mode Quest
EOF
}

cmd_check() {
  local ok=0
  if command -v node >/dev/null 2>&1; then
    echo "ok: node $(node --version)"
  else
    echo "missing: node (need 18+)"; ok=1
  fi
  if command -v npm >/dev/null 2>&1; then
    echo "ok: npm $(npm --version)"
  else
    echo "missing: npm"; ok=1
  fi
  if command -v bubblewrap >/dev/null 2>&1; then
    echo "ok: bubblewrap $(bubblewrap --version 2>/dev/null || echo present)"
  else
    echo "missing: bubblewrap (run: $0 install-cli)"
    ok=1
  fi
  if command -v keytool >/dev/null 2>&1; then
    echo "ok: keytool"
  else
    echo "note: keytool not on PATH (Bubblewrap JDK under ~/.bubblewrap/jdk may still work)"
  fi
  if command -v curl >/dev/null 2>&1; then
    echo "ok: curl"
  else
    echo "missing: curl"; ok=1
  fi
  return "${ok}"
}

cmd_install_cli() {
  command -v npm >/dev/null 2>&1 || die "npm required"
  echo "Installing ${BUBBLEWRAP_PKG} globally (user npm prefix)…"
  npm install --global "${BUBBLEWRAP_PKG}"
  command -v bubblewrap >/dev/null 2>&1 || die "bubblewrap still not on PATH after install"
  bubblewrap --version || true
}

render_templates() {
  need_host
  [[ -n "${FINGERPRINT}" ]] || die "set HANDFORGE_SHA256_FINGERPRINT (from keytool -list -v)"
  local fp
  fp="$(normalize_fingerprint "${FINGERPRINT}")"
  mkdir -p "${GENERATED_DIR}" "${PROJECT_DIR}"
  local ks_path
  ks_path="$(cd "$(dirname "${KEYSTORE_PATH}")" 2>/dev/null && pwd)/$(basename "${KEYSTORE_PATH}")" || ks_path="${KEYSTORE_PATH}"

  sed \
    -e "s|{{HOST}}|${HOST}|g" \
    -e "s|{{KEYSTORE_PATH}}|${ks_path}|g" \
    -e "s|{{KEYSTORE_ALIAS}}|${KEYSTORE_ALIAS}|g" \
    "${BW_DIR}/twa-manifest.template.json" > "${GENERATED_DIR}/twa-manifest.json"

  sed \
    -e "s|{{PACKAGE_ID}}|${PACKAGE_ID}|g" \
    -e "s|{{SHA256_FINGERPRINT}}|${fp}|g" \
    "${BW_DIR}/assetlinks.template.json" > "${GENERATED_DIR}/assetlinks.json"

  cp -f "${GENERATED_DIR}/twa-manifest.json" "${PROJECT_DIR}/twa-manifest.json"
  cp -f "${GENERATED_DIR}/assetlinks.json" "${PROJECT_DIR}/assetlinks.json"

  echo "wrote ${GENERATED_DIR}/twa-manifest.json"
  echo "wrote ${GENERATED_DIR}/assetlinks.json"
  echo "copied into ${PROJECT_DIR}/"
  echo "host=https://${HOST}/  package=${PACKAGE_ID}  mode=2D"
}

cmd_configure() {
  render_templates
}

cmd_publish_assetlinks() {
  local src="${GENERATED_DIR}/assetlinks.json"
  [[ -f "${src}" ]] || die "run configure first (missing ${src})"
  mkdir -p "${STATIC_WELL_KNOWN}"
  cp -f "${src}" "${STATIC_WELL_KNOWN}/assetlinks.json"
  echo "published ${STATIC_WELL_KNOWN}/assetlinks.json"
  echo "Serve the companion over HTTPS so https://${HOST:-<your-host>}/.well-known/assetlinks.json is reachable without auth."
}

cmd_fingerprint() {
  local kt="keytool"
  if ! command -v keytool >/dev/null 2>&1; then
    local found
    found="$(find "${HOME}/.bubblewrap/jdk" -path '*/bin/keytool' 2>/dev/null | head -1 || true)"
    [[ -n "${found}" ]] || die "keytool not found; install a JDK or run bubblewrap once"
    kt="${found}"
  fi
  [[ -f "${KEYSTORE_PATH}" ]] || die "keystore not found: ${KEYSTORE_PATH}"
  echo "Listing ${KEYSTORE_PATH} (alias=${KEYSTORE_ALIAS})…"
  "${kt}" -list -v -keystore "${KEYSTORE_PATH}" -alias "${KEYSTORE_ALIAS}"
}

cmd_build() {
  command -v bubblewrap >/dev/null 2>&1 || die "bubblewrap not found; run: $0 install-cli"
  [[ -f "${PROJECT_DIR}/twa-manifest.json" ]] || die "missing ${PROJECT_DIR}/twa-manifest.json — run configure first"
  if [[ ! -f "${KEYSTORE_PATH}" ]]; then
    die "keystore missing at ${KEYSTORE_PATH}. Create one (keytool -genkeypair …) or set HANDFORGE_KEYSTORE_PATH. Never commit keystores."
  fi
  (
    cd "${PROJECT_DIR}"
    echo "Running bubblewrap update…"
    bubblewrap update --skipVersionUpgrade || bubblewrap update
    echo "Running bubblewrap build…"
    bubblewrap build
  )
  echo "Artifacts (if build succeeded):"
  ls -la "${PROJECT_DIR}"/app-release-signed.apk "${PROJECT_DIR}"/app-release-bundle.aab 2>/dev/null || true
  echo "Sideload: adb install ${PROJECT_DIR}/app-release-signed.apk"
}

cmd_verify_origin() {
  need_host
  command -v curl >/dev/null 2>&1 || die "curl required"
  local base="https://${HOST}"
  echo "GET ${base}/quest.webmanifest"
  curl -fsSL "${base}/quest.webmanifest" | head -c 400
  echo
  echo "GET ${base}/.well-known/assetlinks.json"
  curl -fsSL "${base}/.well-known/assetlinks.json"
  echo
  echo "ok: origin responds over HTTPS for Quest packaging inputs"
}

cmd_doctor() {
  cmd_check || true
  echo
  echo "Next manual steps:"
  echo "  1. Choose a public DNS name and terminate TLS (Caddyfile.example / nginx.conf.example)."
  echo "  2. Run: handforge serve --lan  (token required) behind that reverse proxy."
  echo "  3. Create a signing keystore; export HANDFORGE_SHA256_FINGERPRINT from keytool."
  echo "  4. ${0##*/} configure && ${0##*/} publish-assetlinks && redeploy/restart companion."
  echo "  5. ${0##*/} verify-origin && ${0##*/} build"
  echo "  6. adb install …/app-release-signed.apk on a developer-mode Quest; open from Unknown Sources."
  echo "LAN HTTP (Quest Browser → http://<lan-ip>:8765/quest.html?token=…) remains supported without Bubblewrap."
}

main() {
  local cmd="${1:-help}"
  shift || true
  case "${cmd}" in
    help|-h|--help) cmd_help ;;
    check) cmd_check ;;
    install-cli) cmd_install_cli ;;
    configure) cmd_configure ;;
    publish-assetlinks) cmd_publish_assetlinks ;;
    fingerprint) cmd_fingerprint ;;
    build) cmd_build ;;
    verify-origin) cmd_verify_origin ;;
    doctor) cmd_doctor ;;
    *) die "unknown command: ${cmd} (try: help)" ;;
  esac
}

main "$@"
