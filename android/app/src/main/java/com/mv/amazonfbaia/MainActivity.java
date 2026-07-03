package com.mv.amazonfbaia;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * MV Amazon FBA IA — actividad unica que hospeda la interfaz movil.
 *
 * La UI (HTML/CSS/JS de mobile/) viaja DENTRO del APK como assets, asi que la
 * app abre instantanea y sin depender de ningun hosting; lo unico remoto es la
 * API del negocio (FastAPI en la PC del usuario), cuya URL se configura en la
 * pestana Config y persiste en localStorage del WebView.
 *
 * Sin AppCompat ni librerias: WebView del framework + Activity plana, a
 * proposito — cero dependencias que mantener y un APK minimo.
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
        s.setDomStorageEnabled(true);      // localStorage: guarda la URL de la API
        s.setAllowFileAccess(true);        // assets locales via file://
        s.setLoadsImagesAutomatically(true);
        s.setTextZoom(100);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri url = request.getUrl();
                // La UI vive en assets: cualquier link externo (Alibaba, Amazon,
                // Global Sources...) se abre en el navegador del telefono, no
                // dentro de la app.
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

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        webView.saveState(outState);
    }

    @Override
    public void onBackPressed() {
        // El boton atras navega el historial de la UI antes de salir de la app.
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
