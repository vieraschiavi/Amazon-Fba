import SwiftUI

// MVAmazonFBAIAApp — punto de entrada de la app iOS.
//
// Espejo del proyecto Android: la UI y el motor de negocio (HTML/CSS/JS de
// mobile/, incluido js/nucleo.js) viajan DENTRO de la app como recursos y
// corren en un WKWebView. No depende de ninguna PC ni hosting: abre y
// funciona offline. Ver WebViewContainer.swift para el puente nativo.
@main
struct MVAmazonFBAIAApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .ignoresSafeArea(edges: .bottom)
        }
    }
}
