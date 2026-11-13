#!/bin/bash
# --- ./dist/mac_app_installer/provision.sh ---
# postinstall script .pkg
# root /Applications

set -euo pipefail

APP="${2:?chýba cieľový priečinok}/FUKAI.app"
RES="$APP/Contents/Resources"
INST="$RES/installer"
LOG="${FUKAI_INSTALL_LOG:-/Library/Logs/FUKAI-install.log}"
BACKEND=metal

exec > >(tee -a "$LOG") 2>&1

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*"; }
value() { plutil -extract "$1" raw -o - "$INST/manifest.json"; }

fail() {
    log "CHYBA: $*"
    rm -rf "$RES/env"
    exit 1
}

TMP="$(mktemp -d /tmp/fukai-install.XXXXXX)"
trap 'rm -rf "$TMP" "$INST"' EXIT

log "Inštalácia FUKAI $(value app_version) do $APP"

# --- kontrola HW a OS ----
[ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" = 1 ] || fail "FUKAI potrebuje Mac s čipom Apple (M1 alebo novší)."
need="$(value minimum.macos_version)"
have="$(sw_vers -productVersion)"
[ "${have%%.*}" -ge "${need%%.*}" ] || fail "FUKAI potrebuje macOS $need alebo novší, tento Mac má $have."

# --- stiahnúť llama-cpp-python wheel ---
file="$(value backends.$BACKEND.wheel.file)"
url="$(value releases)/$(value backends.$BACKEND.wheel.release)/$file"
wheel="$TMP/$file"
log "Sťahujem $url"
curl -fsSL --proto '=https' --retry 3 --connect-timeout 20 -o "$wheel" "$url" || fail "Súbor sa nepodarilo stiahnuť. Skontroluj pripojenie na internet a spusti inštaláciu znova."
[ "$(shasum -a 256 "$wheel" | cut -d' ' -f1)" = "$(value backends.$BACKEND.wheel.sha256)" ] || fail "Stiahnutý súbor $file je poškkodený. Spusti inštaláciu znova."

# --- python a venv ---
export UV_NO_CONFIG=1 UV_NO_PROGRESS=1 UV_LINK_MODE=copy
export UV_PYTHON_PREFERENCE=only-managed
export UV_PYTHON_INSTALL_DIR="$RES/python"
export UV_CACHE_DIR="$TMP/cache"
uv="$INST/uv"
python="$(value python)"
env_python="$RES/env/bin/python"
rm -rf "$RES/python" "$RES/env"
log "Inštalujem Python $python"
"$uv" python install --no-bin "$python" || fail "Python sa nepodarilo nainštalovať."
"$uv" venv --python "$python" "$RES/env" || fail "Prostredie aplikácie sa nepodarilo vytvoriť."
log "Inštalujem balíky zo zámku $(value backends.$BACKEND.lock)"
"$uv" pip install --python "$env_python" --require-hashes --compile-bytecode -r "$INST/$(value backends.$BACKEND.lock)" \
    || fail "Balíky sa nepodarilo nainštalovať. Skontroluj pripojenie na internet a spusti inštaláciu znova."
"$uv" pip install --python "$env_python" --no-deps --compile-bytecode "$wheel" || fail "llama-cpp-python sa nepodarilo nainštalovať."
"$env_python" -m compileall -q "$RES/app" || fail "Zdrojový kód aplikácie sa nepodarilo preložiť."

# --- backend test ---
log "Test backendu"
result="$(PYTHONIOENCODING=utf-8 "$env_python" "$INST/backend_test.py" "$RES/app")" || fail "Test backendu zlyhal: $result"
log "$result"
backend="$(printf '%s' "$result" | plutil -extract backend raw -o - - 2>/dev/null || true)"
[ "$backend" = "$BACKEND" ] || fail "Engine nebeží na $BACKEND, ale na ${backend:-?}."

# --- práva ---
if [ "$(id -u)" = 0 ]; then
    chown -R root:wheel "$APP"
fi
chmod -R go-w "$APP"

log "Hotovo"
