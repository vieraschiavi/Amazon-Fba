# MV Amazon FBA IA — App Android nativa

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
`android/` o `mobile/` y lo deja como **artifact descargable** en la pestaña
Actions del repo. También se puede disparar a mano (workflow_dispatch).

## Publicar en Play Store (cuando quieras)

El APK actual está firmado con la clave *debug* estándar: perfecto para
distribución directa e instalación manual, no aceptado por Play Store. Para
publicar: generá tu keystore (`keytool -genkeypair …`), configurá
`signingConfigs` en `app/build.gradle`, compilá `gradle bundleRelease` (AAB) y
subilo a Play Console (cuenta de desarrollador: USD 25 una única vez).
