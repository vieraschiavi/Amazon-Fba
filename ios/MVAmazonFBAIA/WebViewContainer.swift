import SwiftUI
import WebKit

// WebViewContainer — WKWebView que hospeda la interfaz movil (mobile/), con un
// puente nativo equivalente al de Android (PuenteNativo en MainActivity.java):
// window.__puenteResolver + PuenteNativo.postMessage(...) para que app.js pueda
// hacer HTTP sin toparse con las restricciones de CORS/ATS del origen file://.
//
// La UI vive en assets/www dentro del bundle de la app (ver project.yml,
// carpeta "www" copiada desde ../../mobile en cada build).
struct WebViewContainer: UIViewRepresentable {
    func makeCoordinator() -> Coordinator { Coordinator() }

    // app.js espera un objeto global `PuenteNativo.httpRequest(id, metodo, url,
    // cuerpo, cabeceras)` (la API que Android inyecta con addJavascriptInterface).
    // iOS solo ofrece webkit.messageHandlers.postMessage(objeto), asi que este
    // shim traduce una API en la otra sin tocar app.js.
    private static let puenteShim = """
    window.PuenteNativo = {
      httpRequest: function(id, metodo, url, cuerpo, cabeceras) {
        window.webkit.messageHandlers.PuenteNativo.postMessage({
          id: id, method: metodo, url: url, body: cuerpo, headers: cabeceras
        });
      }
    };
    """

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        let controller = WKUserContentController()
        controller.add(context.coordinator, name: "PuenteNativo")
        let script = WKUserScript(source: Self.puenteShim, injectionTime: .atDocumentStart,
                                  forMainFrameOnly: true)
        controller.addUserScript(script)
        config.userContentController = controller
        config.preferences.javaScriptCanOpenWindowsAutomatically = false

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.uiDelegate = context.coordinator
        webView.isOpaque = false
        webView.scrollView.bounces = false
        context.coordinator.webView = webView

        if let url = Bundle.main.url(forResource: "index", withExtension: "html",
                                     subdirectory: "www") {
            webView.loadFileURL(url, allowingReadAccessTo: url.deletingLastPathComponent())
        }
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    final class Coordinator: NSObject, WKScriptMessageHandler, WKNavigationDelegate, WKUIDelegate {
        weak var webView: WKWebView?
        private let session = URLSession(configuration: .default)

        // ---- Puente HTTP: recibe {id, method, url, body, headers} desde app.js ----
        func userContentController(_ userContentController: WKUserContentController,
                                   didReceive message: WKScriptMessage) {
            guard message.name == "PuenteNativo",
                  let dict = message.body as? [String: Any],
                  let id = dict["id"] as? String,
                  let method = dict["method"] as? String,
                  let urlStr = dict["url"] as? String,
                  let url = URL(string: urlStr) else { return }

            var request = URLRequest(url: url)
            request.httpMethod = method.uppercased()
            request.timeoutInterval = 20

            if let headersJson = dict["headers"] as? String,
               let data = headersJson.data(using: .utf8),
               let headers = try? JSONSerialization.jsonObject(with: data) as? [String: String] {
                for (k, v) in headers { request.setValue(v, forHTTPHeaderField: k) }
            }
            if let body = dict["body"] as? String, !body.isEmpty,
               method.uppercased() != "GET", method.uppercased() != "HEAD" {
                request.httpBody = body.data(using: .utf8)
            }

            session.dataTask(with: request) { [weak self] data, response, error in
                let status = (response as? HTTPURLResponse)?.statusCode ?? 0
                let bodyText = data.flatMap { String(data: $0, encoding: .utf8) } ?? ""
                let payload: [String: Any]
                if let error = error {
                    payload = ["error": error.localizedDescription]
                } else {
                    payload = ["status": status, "body": bodyText]
                }
                self?.entregar(id: id, payload: payload)
            }.resume()
        }

        private func entregar(id: String, payload: [String: Any]) {
            guard let data = try? JSONSerialization.data(withJSONObject: payload),
                  let json = String(data: data, encoding: .utf8) else { return }
            let escapedId = id.replacingOccurrences(of: "\"", with: "\\\"")
            let escapedJson = json.replacingOccurrences(of: "\\", with: "\\\\")
                                  .replacingOccurrences(of: "\"", with: "\\\"")
            let js = "window.__puenteResolver && window.__puenteResolver(\"\(escapedId)\", \"\(escapedJson)\")"
            DispatchQueue.main.async { [weak self] in
                self?.webView?.evaluateJavaScript(js, completionHandler: nil)
            }
        }

        // ---- Links externos (Alibaba, Amazon, Global Sources...) al navegador del telefono ----
        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let url = navigationAction.request.url else {
                decisionHandler(.allow); return
            }
            if url.isFileURL || navigationAction.targetFrame != nil && navigationAction.targetFrame!.isMainFrame && url.scheme == "file" {
                decisionHandler(.allow); return
            }
            if url.scheme == "http" || url.scheme == "https" {
                if navigationAction.navigationType == .linkActivated {
                    UIApplication.shared.open(url)
                    decisionHandler(.cancel)
                    return
                }
            }
            decisionHandler(.allow)
        }
    }
}
