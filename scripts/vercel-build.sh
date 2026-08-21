#!/bin/sh
# Copia la PWA (mobile/, solo HTML/CSS/JS) dentro de landing/app/ para que la
# landing pueda linkear una vista de ejemplo, sin exponer el resto del repo
# (backend/Android nativo/iOS nativo) al deploy de Vercel.
#
# IMPORTANTE -- LA DEMO WEB NO LLEVA EL MOTOR
# -------------------------------------------
# Antes se copiaba mobile/js/nucleo.js tal cual: el port fiel de agents/pricing,
# ganancias, exito, dedicacion y capital_planner, con cada formula, umbral y
# curva de BSR, en JavaScript legible. Cualquiera podia abrir el inspector en
# /app/ y llevarse el activo de ingenieria entero -- la competencia incluida.
#
# Ahora se publica nucleo-demo.js RENOMBRADO a nucleo.js: misma API, resultados
# congelados de un producto de ejemplo. Las pantallas se ven igual, el motor no
# viaja. La app instalada y la APK siguen llevando el motor de verdad.
# El test test/verificar_demo_sin_motor.mjs falla si el real vuelve a colarse.
set -e
mkdir -p landing/app/css landing/app/js landing/app/icons
cp mobile/index.html mobile/manifest.json mobile/service-worker.js landing/app/
cp mobile/css/estilos.css landing/app/css/
cp mobile/js/seguro.js mobile/js/licencia.js mobile/js/app.js landing/app/js/
cp mobile/js/nucleo-demo.js landing/app/js/nucleo.js
cp mobile/icons/*.png landing/app/icons/

# Vercel sirve /app/ con trailingSlash=false, redirige a /app y ahí los links
# relativos (css/, js/) se resuelven contra la raiz -> 404 -> demo sin estilo.
# Inyectamos <base href="/app/"> SOLO en la copia web (no en mobile/ original,
# que usa rutas relativas para la app descargada file://) para que TODO resuelva
# bien sin importar la barra final.
sed -i 's#<head>#<head>\n<base href="/app/">#' landing/app/index.html

# Cartel fijo de "datos de ejemplo". La regla del proyecto es no simular nunca
# un resultado haciendolo pasar por real: como esta copia devuelve numeros
# congelados, tiene que decirlo a la vista, no en letra chica. Ademas es el
# lugar natural para el CTA: quien esta mirando la demo es justo quien puede
# pedir la real.
# Delimitador "|" y no "#": el propio cartel lleva colores (#152a63) y un
# ancla (/#solicitar-demo), asi que con "#" sed cortaba el patron al medio.
sed -i 's|<body>|<body>\n<div class="mv-demo-aviso">Vista de ejemplo — los números son fijos y no se recalculan. <a href="https://mvfbaia.com/#solicitar-demo">Pedí la demo real 1:1</a></div>|' landing/app/index.html

# El estilo va en el CSS y no inline: el inline con comillas dobles adentro de
# un sed es justo donde se rompen estas cosas.
cat >> landing/app/css/estilos.css <<'CSS'

/* Cartel de la demo web publica (lo inyecta scripts/vercel-build.sh). */
.mv-demo-aviso{position:sticky;top:0;z-index:9999;background:#152a63;color:#fff;
  padding:9px 14px;font:600 13px/1.45 system-ui,sans-serif;text-align:center}
.mv-demo-aviso a{color:#f0ac3f;text-decoration:underline}
CSS
