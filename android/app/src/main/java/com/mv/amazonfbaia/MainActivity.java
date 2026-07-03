package com.mv.amazonfbaia;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Iterator;

/**
 * MV Amazon FBA IA — actividad unica que hospeda la interfaz movil.
 *
 * La app es NATIVA y AUTOCONTENIDA: toda la UI y el motor de negocio (HTML/CSS/JS
 * de mobile/, incluido js/nucleo.js) viajan DENTRO del APK como assets y corren
 * en el telefono. No depende de ninguna PC ni hosting: abre y funciona offline.
 *
 * Lo unico que necesita internet (keywords reales de Amazon, asistente Claude)
 * usa el internet del celular a traves del PUENTE NATIVO de abajo: hace el HTTP
 * en Java, evitando el bloqueo CORS que sufre el origen file:// del WebView.
 *
 * Sin AppCompat ni librerias pesadas: WebView del framework + Activity plana.
 */
public class MainActivity extends Activity {

    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        webView = new WebView(this);
        setContentView(webView);

        // Barra de estado en navy de marca, iconos claros.
        getWindow().setStatusBarColor(Color.parseColor("#152A63"));
        getWindow().setNavigationBarColor(Color.parseColor("#FFFFFF"));
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
        }

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);      // la UI es una SPA en JS
        s.setDomStorageEnabled(true);      // localStorage: portafolio, ventas, claves
        s.setAllowFileAccess(true);        // assets locales via file://
        s.setLoadsImagesAutomatically(true);
        s.setTextZoom(100);
        // Viewport correcto en cualquier WebView: usa el <meta viewport> de la
        // pagina y no arranca "zoomeado".
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        s.setBuiltInZoomControls(false);
        s.setSupportZoom(false);

        // Puente nativo: la UI llama a PuenteNativo.httpRequest(...) para las
        // pocas cosas que necesitan internet, sin toparse con CORS.
        webView.addJavascriptInterface(new PuenteNativo(), "PuenteNativo");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri url = request.getUrl();
                // La UI vive en assets: cualquier link externo (Alibaba, Amazon,
                // Global Sources...) se abre en el navegador del telefono.
                if ("file".equals(url.getScheme())) {
                    return false;
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, url));
                } catch (Exception ignored) {
                    // sin navegador instalado: no romper la app por un link
                }
                return true;
            }
        });

        if (savedInstanceState == null) {
            webView.loadUrl("file:///android_asset/www/index.html");
        } else {
            webView.restoreState(savedInstanceState);
        }
    }

    /**
     * Puente HTTP para el JS. Corre la peticion en un hilo aparte y devuelve el
     * resultado al WebView invocando window.__puenteResolver(id, respuestaJSON).
     * La respuesta es {status, body} o {error} — el mismo contrato que espera
     * pedirHTTP() en app.js.
     */
    private class PuenteNativo {
        @JavascriptInterface
        public void httpRequest(final String id, final String metodo, final String url,
                                final String cuerpo, final String cabecerasJson) {
            new Thread(new Runnable() {
                @Override
                public void run() {
                    String resultado;
                    try {
                        resultado = ejecutar(metodo, url, cuerpo, cabecerasJson);
                    } catch (Exception e) {
                        resultado = "{\"error\":" + JSONObject.quote(String.valueOf(e.getMessage())) + "}";
                    }
                    entregar(id, resultado);
                }
            }).start();
        }

        private String ejecutar(String metodo, String urlStr, String cuerpo,
                                String cabecerasJson) throws Exception {
            HttpURLConnection con = (HttpURLConnection) new URL(urlStr).openConnection();
            con.setRequestMethod(metodo == null ? "GET" : metodo.toUpperCase());
            con.setConnectTimeout(15000);
            con.setReadTimeout(20000);
            con.setInstanceFollowRedirects(true);
            if (cabecerasJson != null && !cabecerasJson.isEmpty()) {
                try {
                    JSONObject h = new JSONObject(cabecerasJson);
                    for (Iterator<String> it = h.keys(); it.hasNext(); ) {
                        String k = it.next();
                        con.setRequestProperty(k, h.getString(k));
                    }
                } catch (Exception ignored) { }
            }
            if (cuerpo != null && !cuerpo.isEmpty()
                    && !"GET".equalsIgnoreCase(metodo) && !"HEAD".equalsIgnoreCase(metodo)) {
                con.setDoOutput(true);
                byte[] datos = cuerpo.getBytes(StandardCharsets.UTF_8);
                OutputStream os = con.getOutputStream();
                os.write(datos);
                os.close();
            }
            int code = con.getResponseCode();
            InputStream is = (code >= 200 && code < 400) ? con.getInputStream() : con.getErrorStream();
            String body = is == null ? "" : leer(is);
            con.disconnect();
            JSONObject out = new JSONObject();
            out.put("status", code);
            out.put("body", body);
            return out.toString();
        }

        private String leer(InputStream is) throws Exception {
            BufferedReader br = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            String linea;
            while ((linea = br.readLine()) != null) {
                sb.append(linea).append('\n');
            }
            br.close();
            return sb.toString().trim();
        }
    }

    /** Devuelve el resultado al JS en el hilo de UI. */
    private void entregar(final String id, final String resultadoJson) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (webView == null) return;
                String js = "window.__puenteResolver && window.__puenteResolver("
                        + JSONObject.quote(id) + "," + JSONObject.quote(resultadoJson) + ")";
                webView.evaluateJavascript(js, null);
            }
        });
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        webView.saveState(outState);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }
}
