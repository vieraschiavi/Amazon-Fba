#!/usr/bin/env bash
# build-apk.sh — Compila el APK de MV Amazon FBA IA y lo deja firmado con los
# TRES esquemas (v1 JAR + v2 + v3) para que lo reconozca CUALQUIER instalador de
# APK y cualquier Android 7+.
#
# Por que v1: el Android Gradle Plugin, con minSdk 24, descarta la firma v1 (le
# alcanza v2). Pero varios instaladores de APK de terceros y equipos Android 7-9
# solo detectan el paquete si tiene v1. Por eso re-firmamos con apksigner
# forzando --min-sdk-version 19, que obliga a incluir v1.
#
# Salida: android/app/build/outputs/apk/release/MV-Amazon-FBA-IA.apk
set -euo pipefail

cd "$(dirname "$0")"
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-/opt/android-sdk}}"
BT="$(ls -d "$SDK"/build-tools/* | sort -V | tail -1)"
APKSIGNER="$BT/apksigner"
ZIPALIGN="$BT/zipalign"
KS="app/mv-release.keystore"
STOREPASS="${MV_KS_PASS:-mvfba2026}"

GRADLE="${GRADLE_BIN:-gradle}"
echo "==> gradle assembleRelease"
"$GRADLE" assembleRelease

RAW="app/build/outputs/apk/release/app-release.apk"
FINAL="app/build/outputs/apk/release/MV-Amazon-FBA-IA.apk"

echo "==> re-firmando con v1+v2+v3 (apksigner, min-sdk 19)"
"$APKSIGNER" sign \
  --ks "$KS" --ks-key-alias mvfba \
  --ks-pass "pass:$STOREPASS" --key-pass "pass:$STOREPASS" \
  --min-sdk-version 19 \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  --out "$FINAL" "$RAW"

echo "==> verificando firma (los tres esquemas deben dar true)"
"$APKSIGNER" verify --min-sdk-version 19 --verbose "$FINAL" | grep -E "Verified using v[123]"
"$ZIPALIGN" -c -v 4 "$FINAL" >/dev/null && echo "zipalign OK"

echo "==> LISTO: $FINAL"
ls -la "$FINAL"
