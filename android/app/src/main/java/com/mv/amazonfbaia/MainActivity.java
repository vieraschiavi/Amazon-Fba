// © 2026 Martín Viera. Todos los derechos reservados.
package com.mv.amazonfbaia;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Iterator;

/**
 * MV FBA IA — actividad unica que hospeda la interfaz movil.
 *
 * La app es NATIVA y AUTOCONTENIDA: toda la UI y el motor de negocio (HTML/CSS/JS
 * de mobile/, incluido js/nucleo.js) viajan DENTRO del APK como assets y corren
 * en el telefono. No depende de ninguna PC ni hosting: abre y funciona offline.
 *
 * Lo unico que necesita internet (keywords reales de Amazon, asistente Claude)
 * usa el internet del celular a traves del PUENTE NATIVO de abajo, que hace el
 * HTTP en Java para evitar el bloqueo CORS del origen file:// del WebView.
 *
 * A prueba de crashes: si algo falla al arrancar, en vez de "abrir y cerrar" en
 * silencio, la app guarda el error y lo MUESTRA en pantalla (seleccionable) para
 * poder diagnosticarlo. Ver capturarError()/mostrarError().
 */
public class MainActivity extends Activity {

    private static final String ARCHIVO_ERROR = "ultimo_error.txt";
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 1) Cualquier excepcion no atrapada (incluida la inflacion del primer
        //    frame) se guarda a disco antes de que el proceso muera.
        final Thread.UncaughtExceptionHandler previo = Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler(new Thread.UncaughtExceptionHandler() {
            @Override
            public void uncaughtException(Thread t, Throwable e) {
                guardarError(e);
                if (previo != null) previo.uncaughtException(t, e);
            }
        });

        // 2) Si en el arranque anterior hubo un crash, mostramos el detalle en
        //    vez de volver a intentar (y volver a cerrarse). El usuario puede
        //    leerlo, copiarlo y mandarlo; o tocar "Reintentar".
        File err = new File(getFilesDir(), ARCHIVO_ERROR);
        if (err.exists()) {
            String detalle = leerArchivo(err);
            err.delete();
            mostrarError(detalle);
            return;
        }

        // 3) Arranque normal, protegido: si tira algo sincronico, lo mostramos ya.
        try {
            arrancar(savedInstanceState);
        } catch (Throwable t) {
            guardarError(t);
            mostrarError(traza(t));
        }
    }

    /** Toda la inicializacion real de la app. */
    private void arrancar(Bundle savedInstanceState) {
        webView = new WebView(this);
        setContentView(webView);

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
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(true);
        s.setBuiltInZoomControls(false);
        s.setSupportZoom(false);

        webView.addJavascriptInterface(new PuenteNativo(), "PuenteNativo");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri url = request.getUrl();
                if ("file".equals(url.getScheme())) {
                    return false;
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, url));
                } catch (Exception ignored) {
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

    // ------------------------------------------------------ diagnostico de crash
    private void guardarError(Throwable t) {
        try {
            String txt = "MV FBA IA — error de arranque\n"
                    + "versionName 1.1.3\n"
                    + "Android " + Build.VERSION.RELEASE + " (API " + Build.VERSION.SDK_INT + ")\n"
                    + Build.MANUFACTURER + " " + Build.MODEL + "\n\n" + traza(t);
            FileOutputStream fos = openFileOutput(ARCHIVO_ERROR, MODE_PRIVATE);
            fos.write(txt.getBytes(StandardCharsets.UTF_8));
            fos.close();
        } catch (Throwable ignore) {
        }
    }

    private String traza(Throwable t) {
        StringWriter sw = new StringWriter();
        t.printStackTrace(new PrintWriter(sw));
        return sw.toString();
    }

    private void mostrarError(String detalle) {
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        col.setBackgroundColor(Color.parseColor("#152A63"));
        int pad = (int) (16 * getResources().getDisplayMetrics().density);
        col.setPadding(pad, pad * 3, pad, pad);

        TextView titulo = new TextView(this);
        titulo.setText("La app se cerro por este error");
        titulo.setTextColor(Color.WHITE);
        titulo.setTextSize(18);
        titulo.setPadding(0, 0, 0, pad);
        col.addView(titulo);

        TextView sub = new TextView(this);
        sub.setText("Copiá este texto (mantené apretado) y mandámelo para arreglarlo:");
        sub.setTextColor(Color.parseColor("#CBD5E1"));
        sub.setTextSize(13);
        sub.setPadding(0, 0, 0, pad);
        col.addView(sub);

        TextView tv = new TextView(this);
        tv.setText(detalle);
        tv.setTextColor(Color.parseColor("#8BC34A"));
        tv.setTextSize(12);
        tv.setTextIsSelectable(true);
        tv.setTypeface(android.graphics.Typeface.MONOSPACE);
        ScrollView sv = new ScrollView(this);
        sv.addView(tv);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f);
        col.addView(sv, lp);

        Button reintentar = new Button(this);
        reintentar.setText("Reintentar");
        reintentar.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                recreate();
            }
        });
        col.addView(reintentar);

        setContentView(col);
    }

    /**
     * Puente HTTP para el JS. Corre la peticion en un hilo aparte y devuelve el
     * resultado al WebView invocando window.__puenteResolver(id, respuestaJSON).
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

    private String leerArchivo(File f) {
        try {
            BufferedReader br = new BufferedReader(new InputStreamReader(
                    new java.io.FileInputStream(f), StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            String linea;
            while ((linea = br.readLine()) != null) sb.append(linea).append('\n');
            br.close();
            return sb.toString();
        } catch (Throwable t) {
            return "(no se pudo leer el detalle del error)";
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        if (webView != null) webView.saveState(outState);
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
