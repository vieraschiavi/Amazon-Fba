# MV Amazon FBA IA — App iOS (iPhone / iPad / Mac vía Catalyst)

App nativa que hospeda la misma interfaz movil (`mobile/`) en un `WKWebView`,
con un puente nativo equivalente al de Android (`WebViewContainer.swift`).
Mismo motor, misma UI, mismo `nucleo.js` — corre offline en el telefono.

## Compilar en tu Mac

Necesitás **Xcode** (gratis, App Store) y **XcodeGen** (`brew install xcodegen`).

```bash
cd ios
xcodegen generate          # genera MVAmazonFBAIA.xcodeproj desde project.yml
open MVAmazonFBAIA.xcodeproj
```

En Xcode: elegí un simulador (o tu iPhone) y ▶ Run. Para simulador no hace
falta firma ni cuenta de Apple.

## Lo que hace falta para instalar en un iPhone real / subir a la App Store

Esto **no lo puede generar ningún asistente ni CI**: Apple lo exige de tu lado.

1. **Cuenta Apple Developer** (individual, US$99/año) en developer.apple.com.
2. En Xcode → pestaña *Signing & Capabilities* → elegí tu **Team** (tu cuenta).
   Xcode gestiona el certificado y el perfil de aprovisionamiento solo.
3. **Dispositivo propio (sideload/testing):** conectá el iPhone por cable,
   seleccionalo como destino y ▶ Run — dura 7 días sin cuenta paga, o
   indefinido con la cuenta de US$99/año.
4. **Distribución a otros (TestFlight / App Store):** Product → Archive →
   Distribute App. Requiere la cuenta paga y pasar la revisión de Apple.

## CI

`.github/workflows/ios-build.yml` corre en un runner `macos-latest` (gratis en
GitHub Actions) y compila la app para el **Simulador de iOS** en cada push —
confirma que el proyecto compila sin errores, sin necesitar tu cuenta de Apple
ni certificados. No genera un `.ipa` instalable en un iPhone real: eso requiere
firma con tu cuenta de Developer (ver arriba). Si más adelante querés que el
CI también firme y publique en TestFlight automáticamente, hay que cargar tus
certificados como secrets del repo (con `fastlane match` o similar) — es un
paso aparte que se hace cuando tengas la cuenta.

## Estructura

```
ios/
├── project.yml              Especificacion XcodeGen (equivalente a build.gradle)
├── MVAmazonFBAIA/
│   ├── MVAmazonFBAIAApp.swift   Punto de entrada (SwiftUI)
│   ├── ContentView.swift        Vista raiz
│   ├── WebViewContainer.swift   WKWebView + puente nativo (equivalente a
│   │                            PuenteNativo de MainActivity.java)
│   ├── Info.plist
│   └── Assets.xcassets/         Icono (logo MV) + color de acento (navy)
└── README.md
```
