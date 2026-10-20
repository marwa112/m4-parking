#!/usr/bin/env bash
# Generates the Android project from the web app in ../docs. Run inside app/.
set -euo pipefail
rm -rf www && mkdir www
cp -r ../docs/. www/
rm -f www/sw.js www/.nojekyll            # the app ships its own files; no service worker needed
[ -d android ] || npx cap add android
npx cap sync android
M=android/app/src/main/AndroidManifest.xml
grep -q ACCESS_FINE_LOCATION "$M" || sed -i 's#</manifest>#    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />\n    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />\n    <uses-feature android:name="android.hardware.location.gps" android:required="false" />\n</manifest>#' "$M"
# App icon: replace the default Capacitor icon with ours (legacy PNG icons, no adaptive XML)
RES=android/app/src/main/res
rm -rf "$RES/mipmap-anydpi-v26"
python3 - "$RES" <<'PY'
import sys
from PIL import Image
res = sys.argv[1]
src = Image.open("../docs/icons/icon-1024.png").convert("RGBA")
for d, px in {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}.items():
    im = src.resize((px, px), Image.LANCZOS)
    for name in ("ic_launcher.png", "ic_launcher_round.png", "ic_launcher_foreground.png"):
        im.save(f"{res}/mipmap-{d}/{name}")
PY
# Version from the CI run number so each APK is newer than the last
if [ -n "${BUILD_NUMBER:-}" ]; then
  sed -i "s/versionCode [0-9]*/versionCode ${BUILD_NUMBER}/; s/versionName \"[^\"]*\"/versionName \"1.${BUILD_NUMBER}\"/" android/app/build.gradle
fi
# Splash screen: our sign on the app's blue instead of the Capacitor logo
python3 - "$RES" <<'PY'
import sys, glob
from PIL import Image
res = sys.argv[1]
icon = Image.open("../docs/icons/icon-1024.png").convert("RGBA")
for f in glob.glob(f"{res}/drawable*/splash.png"):
    w, h = Image.open(f).size
    bg = Image.new("RGBA", (w, h), (11, 92, 173, 255))
    s = int(min(w, h) * 0.4)
    bg.alpha_composite(icon.resize((s, s), Image.LANCZOS), ((w - s) // 2, (h - s) // 2))
    bg.convert("RGB").save(f)
PY
