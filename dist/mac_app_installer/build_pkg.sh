#!/bin/bash
# --- ./dist/mac_app_installer/build_pkg.sh ---
# .pkg builder

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DIST="$(dirname "$HERE")"
REPO="$(dirname "$DIST")"
MANIFEST="$DIST/manifest.json"
OUT="$DIST/out"
ID=sk.vavro.fukai
BACKEND=metal
SOURCES=(core ui storage extensions vars assets main.py)

value() { plutil -extract "$1" raw -o - "$MANIFEST"; }
fail() { echo "CHYBA: $*" >&2; exit 1; }

VERSION="$(value app_version)"
MINOS="$(value minimum.macos_version)"
PY="$(value python)"
PYNAME="cpython-$PY-macos-aarch64-none"
PYLIB="python${PY%.*}"

# --- kontrola ---
for tool in clang codesign install_name_tool pkgbuild productbuild; do
    command -v "$tool" >/dev/null || fail "Chýba $tool – nainštaluj Xcode Command Line Tools (xcode-select --install)."
done
grep -q "^APP_VERSION = \"$VERSION\"$" "$REPO/core/constants.py" || fail "APP_VERSION v core/constants.py nie je $VERSION ako v manifeste."
[ "$(plutil -extract CFBundleShortVersionString raw -o - "$HERE/Info.plist")" = "$VERSION" ] || fail "CFBundleShortVersionString v Info.plist nie je $VERSION ako v manifeste."
[ "$(plutil -extract LSMinimumSystemVersion raw -o - "$HERE/Info.plist")" = "$MINOS" ] || fail "LSMinimumSystemVersion v Info.plist nie je $MINOS ako v manifeste."
if [ -n "$(git -C "$REPO" status --porcelain -- "${SOURCES[@]}")" ]; then
    echo "POZOR: zdrojáky majú necommitnuté zmeny, balia sa tak, ako sú na disku."
fi

BUILD="$(mktemp -d /tmp/fukai-build.XXXXXX)"
trap 'rm -rf "$BUILD"' EXIT
CONTENTS="$BUILD/root/FUKAI.app/Contents"
INST="$CONTENTS/Resources/installer"
mkdir -p "$CONTENTS/MacOS" "$CONTENTS/Resources/app" "$INST/locks" "$BUILD/scripts" "$BUILD/pkgs" "$BUILD/resources" "$OUT"

# --- uv ---
echo "uv $(value uv.version)"
curl -fsSL --proto '=https' --retry 3 -o "$BUILD/uv.tar.gz" "$(value uv.macos.url)" || fail "uv sa nepodarilo stiahnuť."
[ "$(shasum -a 256 "$BUILD/uv.tar.gz" | cut -d' ' -f1)" = "$(value uv.macos.sha256)" ] || fail "uv: nesedí SHA-256."
tar -xzf "$BUILD/uv.tar.gz" -C "$BUILD"
cp "$BUILD/uv-aarch64-apple-darwin/uv" "$INST/uv"

# --- spúšťač ---
echo "Python $PY a spúšťač"
UV_NO_CONFIG=1 UV_NO_PROGRESS=1 UV_PYTHON_PREFERENCE=only-managed \
UV_PYTHON_INSTALL_DIR="$BUILD/python" UV_CACHE_DIR="$BUILD/cache" \
    "$INST/uv" python install --no-bin "$PY"
PYDIR="$BUILD/python/$PYNAME"
[ -d "$PYDIR" ] || fail "Python nie je v $PYDIR."
clang -O2 -Wall -Wextra -Werror -mmacosx-version-min="$MINOS" -I"$PYDIR/include/$PYLIB" \
    "$HERE/launcher.c" -L"$PYDIR/lib" -l"$PYLIB" -framework CoreFoundation -o "$BUILD/FUKAI"
lib="$(otool -L "$BUILD/FUKAI" | awk "/lib$PYLIB.dylib/ {print \$1}")"
install_name_tool -change "$lib" "@rpath/lib$PYLIB.dylib" -add_rpath "@executable_path/../Resources/python/$PYNAME/lib" "$BUILD/FUKAI"
codesign -s - -f -i "$ID" "$BUILD/FUKAI"
cp "$BUILD/FUKAI" "$CONTENTS/MacOS/FUKAI"

# --- obsah bundlu ---
cp "$HERE/Info.plist" "$CONTENTS/Info.plist"
cp "$REPO/assets/icns/fukai.icns" "$CONTENTS/Resources/"
cp "$REPO/LICENSE" "$REPO/THIRD_PARTY_LICENSES.md" "$CONTENTS/Resources/"
git -C "$REPO" ls-files -z -- "${SOURCES[@]}" | (cd "$REPO" && xargs -0 tar -cf -) | tar -xf - -C "$CONTENTS/Resources/app"
cp "$MANIFEST" "$DIST/backend_test.py" "$INST/"
cp "$DIST/$(value backends.$BACKEND.lock)" "$INST/locks/"
xattr -cr "$BUILD/root/FUKAI.app"

# --- balík ---
cp "$HERE/provision.sh" "$BUILD/scripts/postinstall"
chmod 755 "$BUILD/scripts/postinstall"
pkgbuild --analyze --root "$BUILD/root" "$BUILD/component.plist" >/dev/null
plutil -replace 0.BundleIsRelocatable -bool NO "$BUILD/component.plist"
pkgbuild --root "$BUILD/root" --component-plist "$BUILD/component.plist" \
    --identifier "$ID" --version "$VERSION" --install-location /Applications \
    --scripts "$BUILD/scripts" "$BUILD/pkgs/FUKAI-app.pkg"

cp "$HERE/welcome.html" "$BUILD/resources/"
cat > "$BUILD/distribution.xml" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
    <title>FUKAI $VERSION</title>
    <welcome file="welcome.html" mime-type="text/html"/>
    <options customize="never" require-scripts="false" hostArchitectures="arm64"/>
    <domains enable_localSystem="true" enable_currentUserHome="false" enable_anywhere="false"/>
    <volume-check>
        <allowed-os-versions><os-version min="$MINOS"/></allowed-os-versions>
    </volume-check>
    <choices-outline>
        <line choice="$ID"/>
    </choices-outline>
    <choice id="$ID" visible="false">
        <pkg-ref id="$ID"/>
    </choice>
    <pkg-ref id="$ID" version="$VERSION" onConclusion="none">FUKAI-app.pkg</pkg-ref>
</installer-gui-script>
EOF
productbuild --distribution "$BUILD/distribution.xml" --package-path "$BUILD/pkgs" --resources "$BUILD/resources" "$OUT/FUKAI-$VERSION.pkg"

echo "Hotovo: $OUT/FUKAI-$VERSION.pkg ($(du -h "$OUT/FUKAI-$VERSION.pkg" | cut -f1))"
echo "SHA-256 $(shasum -a 256 "$OUT/FUKAI-$VERSION.pkg" | cut -d' ' -f1)"
