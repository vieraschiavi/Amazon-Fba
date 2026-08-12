# MV FBA IA — App Android nativa

Proyecto Android **nativo** (Gradle + Java, sin frameworks intermedios): una
`Activity` con WebView del sistema que embebe la interfaz móvil (`mobile/`)
**dentro del APK**. La app abre instantánea, funciona sin ningún hosting web y
lo único que necesita es alcanzar la API del negocio (se configura en la
pestaña Config de la propia app y queda guardada).

Decisiones de diseño:

- **Cero dependencias** (ni AppCompat, ni Kotlin runtime, ni Capacitor): el APK
  pesa ~80 KB, compila en segundos y no hay librerías que mantener.
- **Una sola fuente de verdad para la UI**: la tarea Gradle `syncWebAssets`
  copia `mobile/` a los assets del APK en cada build. Nunca se edita la UI acá.
- **Ícono adaptativo** de marca (monograma MV) en todas las densidades +
  splash navy al abrir.
- Los **links externos** (Alibaba, Amazon, etc.) se abren en el navegador del
  teléfono, no dentro de la app.
- `usesCleartextTraffic="true"` porque la API corre por HTTP plano en la red
  local del usuario (`http://192.168.x.x:8000`).

## Instalar el APK ya compilado

1. Pasá `MV-Amazon-FBA-IA.apk` al teléfono (WhatsApp a vos mismo, cable, Drive…).
2. Tocalo → Android va a pedir permitir "instalar apps desconocidas" para esa
   fuente (normal para cualquier APK fuera de Play Store) → Instalar.
3. Abrí la app → pestaña **Config** → escribí la URL de tu API
   (ej. `http://192.168.0.10:8000`, la IP local de la PC donde corre
   `API.bat`/`INICIAR.bat`) → Guardar. El teléfono debe estar en la misma WiFi.

## Compilar vos mismo

Requisitos: JDK 17+, Android SDK (platform 34 + build-tools 34) y Gradle 8.9+.

```bash
export ANDROID_HOME=/ruta/al/android-sdk
cd android
gradle assembleDebug
# APK en: app/build/outputs/apk/debug/app-debug.apk
```

O abrí la carpeta `android/` directamente con **Android Studio** (detecta todo
solo) y tocá Run.

### Compilación automática en GitHub (sin instalar nada)

`.github/workflows/android-apk.yml` compila el APK en cada push que toque
`android/` o `mobile/` y lo publica en el Release `android-latest` (y como
artifact descargable en la pestaña Actions). También se puede disparar a mano
(workflow_dispatch).

## Firma del APK (keystore)

Tanto `release` como `debug` se firman con el mismo keystore de distribución
(`signingConfigs.release` en `app/build.gradle`) — así el sideload y los
updates identifican siempre al mismo emisor. El keystore **no vive en el
repo**: ni el archivo `.keystore` ni la contraseña se commitean (antes sí
se commiteaban, en texto plano — se rotó la clave y se sacó del árbol el
`2026-08-12`; ver el historial de `build.gradle` si buscás el porqué).

Tres variables de entorno, sin default de repuesto — si falta alguna, el
build corta con un mensaje claro en vez de arrancar sin firmar:

| Variable | Qué es |
|---|---|
| `MVFBA_KEYSTORE_PATH` | Ruta al `.keystore`, relativa a `android/app/` (default: `mv-release.keystore`) |
| `MVFBA_KEYSTORE_PASSWORD` | Contraseña del keystore (PKCS12: misma para store y key, sin default) |
| `MVFBA_KEY_ALIAS` | Alias de la clave dentro del keystore (default: `mvfba-release`) |

**En CI** (`.github/workflows/android-apk.yml`) salen de tres GitHub Actions
Secrets del repo: `MVFBA_KEYSTORE_BASE64` (el `.keystore` codificado en
base64: `base64 -w0 mv-release.keystore`), `MVFBA_KEYSTORE_PASSWORD` y
`MVFBA_KEY_ALIAS`. El workflow decodifica el primero a un archivo temporal
que se borra apenas termina de usarse — el runner completo se destruye al
cerrar el job de todas formas.

**Localmente**, poné tu copia del `.keystore` en `android/app/` (está en
`.gitignore`, nunca se va a commitear por accidente) y exportá las mismas
tres variables antes de compilar:

```bash
export MVFBA_KEYSTORE_PASSWORD='tu-contraseña'
export MVFBA_KEY_ALIAS='mvfba-release'
cd android && bash build-apk.sh
```

**Si perdés el keystore**, no hay forma de recuperarlo (no hay backdoor ni
recuperación por contraseña): significa firmar la próxima versión con una
clave nueva, y cualquiera que ya haya instalado una versión anterior no
puede actualizar sin desinstalar primero. Guardalo en un lugar que seguro no
pierdas (gestor de contraseñas, backup cifrado) — es, literalmente, la
identidad de la app.

## Publicar en Play Store (cuando quieras)

El keystore de distribución de arriba también sirve para Play Store: compilá
`gradle bundleRelease` (genera un `.aab`, no un `.apk`) con las mismas
variables de entorno cargadas, y subilo a Play Console (cuenta de
desarrollador: USD 25 única vez). Play Store exige el MISMO keystore en cada
actualización para siempre — por eso la nota de arriba sobre no perderlo
importa el doble una vez publicada.
