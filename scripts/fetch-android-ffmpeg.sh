#!/usr/bin/env bash
# Fetch multi-ABI Android FFmpeg prebuilts into the companion jniLibs tree.
#
# Source: husen-hn/ffmpeg-android-binary v2.0.0 (FFmpeg 7.1, NDK r26b, LGPL).
# Layout after install (gitignored *.so blobs):
#   companions/android/android/app/src/main/jniLibs/<abi>/libffmpeg.so   # ffmpeg CLI
#   companions/android/android/app/src/main/jniLibs/<abi>/libav*.so      # runtime deps
#
# Usage:
#   ./scripts/fetch-android-ffmpeg.sh              # armeabi-v7a + arm64-v8a
#   ./scripts/fetch-android-ffmpeg.sh --with-x86_64
#   ./scripts/fetch-android-ffmpeg.sh --check      # verify layout only
#   ./scripts/fetch-android-ffmpeg.sh --clean
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JNILIBS="${ROOT}/companions/android/android/app/src/main/jniLibs"
CACHE="${ROOT}/.cache/android-ffmpeg"
RELEASE="v2.0.0"
BASE_URL="https://github.com/husen-hn/ffmpeg-android-binary/releases/download/${RELEASE}"

declare -A SHA256=(
  [armeabi-v7a]="8e8d858e0277ee12d4217599fbf7e6a309efef9f60c8972e915fa3d9148bd4d7"
  [arm64-v8a]="a7085d380586aed79f8d12a294ee294025a4ce05ebb2e44caad4928073a64293"
  [x86_64]="d40632699db84959335ec49dda25169acdbe82dabf5b14b18e9501d8da6773c9"
)

ABIS=(armeabi-v7a arm64-v8a)
WITH_X86=0
MODE=fetch

usage() {
  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-x86_64) WITH_X86=1; shift ;;
    --check) MODE=check; shift ;;
    --clean) MODE=clean; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ "$WITH_X86" -eq 1 ]]; then
  ABIS+=(x86_64)
fi

required_files_for_abi() {
  local abi="$1"
  echo "${JNILIBS}/${abi}/libffmpeg.so"
  for lib in libavcodec.so libavdevice.so libavfilter.so libavformat.so \
             libavutil.so libpostproc.so libswresample.so libswscale.so; do
    echo "${JNILIBS}/${abi}/${lib}"
  done
}

check_layout() {
  local ok=1
  for abi in "${ABIS[@]}"; do
    while IFS= read -r path; do
      if [[ ! -f "$path" ]]; then
        echo "MISSING: $path" >&2
        ok=0
      fi
    done < <(required_files_for_abi "$abi")
  done
  if [[ "$ok" -ne 1 ]]; then
    echo "Bundled FFmpeg jniLibs incomplete. Run: ./scripts/fetch-android-ffmpeg.sh" >&2
    return 1
  fi
  echo "OK: bundled FFmpeg present for: ${ABIS[*]}"
  return 0
}

clean_libs() {
  for abi in armeabi-v7a arm64-v8a x86_64; do
    local dir="${JNILIBS}/${abi}"
    [[ -d "$dir" ]] || continue
    find "$dir" -type f \( -name 'libffmpeg.so' -o -name 'libav*.so' -o -name 'libsw*.so' -o -name 'libpostproc.so' \) -delete
  done
  echo "Removed bundled FFmpeg blobs under ${JNILIBS}"
}

download_and_install() {
  mkdir -p "$CACHE" "$JNILIBS"
  command -v curl >/dev/null || { echo "curl required" >&2; exit 1; }
  command -v unzip >/dev/null || { echo "unzip required" >&2; exit 1; }
  command -v sha256sum >/dev/null || { echo "sha256sum required" >&2; exit 1; }

  local abi zip url expected actual tmp
  for abi in "${ABIS[@]}"; do
    zip="${CACHE}/${abi}-${RELEASE}.zip"
    url="${BASE_URL}/${abi}.zip"
    expected="${SHA256[$abi]}"
    echo "→ ${abi}: ${url}"
    if [[ -f "$zip" ]]; then
      actual="$(sha256sum "$zip" | awk '{print $1}')"
      if [[ "$actual" != "$expected" ]]; then
        echo "  cache checksum mismatch; re-downloading"
        rm -f "$zip"
      fi
    fi
    if [[ ! -f "$zip" ]]; then
      curl -fL --retry 3 --retry-delay 2 -o "$zip" "$url"
    fi
    actual="$(sha256sum "$zip" | awk '{print $1}')"
    if [[ "$actual" != "$expected" ]]; then
      echo "SHA256 mismatch for ${abi}.zip" >&2
      echo "  expected: ${expected}" >&2
      echo "  actual:   ${actual}" >&2
      exit 1
    fi

    tmp="$(mktemp -d "${CACHE}/extract-${abi}.XXXXXX")"
    unzip -q -o "$zip" -d "$tmp"
    local src="${tmp}/${abi}"
    if [[ ! -x "${src}/bin/ffmpeg" ]]; then
      echo "ffmpeg binary missing in ${abi}.zip" >&2
      rm -rf "$tmp"
      exit 1
    fi
    local dest="${JNILIBS}/${abi}"
    mkdir -p "$dest"
    # PackageManager only extracts lib*.so; rename CLI so it lands in nativeLibraryDir.
    install -m 0755 "${src}/bin/ffmpeg" "${dest}/libffmpeg.so"
    for so in "${src}/lib/"*.so; do
      install -m 0644 "$so" "${dest}/$(basename "$so")"
    done
    # Keep a small committed-friendly marker (text only).
    printf '%s\n' "source=${BASE_URL}/${abi}.zip" "release=${RELEASE}" "sha256=${expected}" \
      > "${dest}/.ffmpeg-source.txt"
    rm -rf "$tmp"
    echo "  installed → ${dest}/libffmpeg.so (+ $(ls "${dest}"/lib*.so 2>/dev/null | wc -l) libs)"
  done

  # Empty placeholder dirs so the tree exists without blobs.
  for abi in armeabi-v7a arm64-v8a; do
    mkdir -p "${JNILIBS}/${abi}"
    touch "${JNILIBS}/${abi}/.gitkeep"
  done

  cat > "${JNILIBS}/README.md" <<'EOF'
# Bundled FFmpeg (`libffmpeg.so`)

Prebuilt binaries are **not** committed (large + LGPL redistributable). Fetch them:

```bash
./scripts/fetch-android-ffmpeg.sh
# optional emulator ABI:
./scripts/fetch-android-ffmpeg.sh --with-x86_64
```

Then build the APK (`./gradlew assembleDebug`). Termux remains the fallback when these files are absent.
EOF

  check_layout
  echo "Done. Rebuild the APK to embed the bundled backend."
}

case "$MODE" in
  check) check_layout ;;
  clean) clean_libs ;;
  fetch) download_and_install ;;
esac
