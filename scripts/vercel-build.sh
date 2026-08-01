#!/bin/sh
# Copia la PWA (mobile/, solo HTML/CSS/JS) dentro de landing/app/ para que la
# landing pueda linkear una demo real y usable ("Probar demo"), sin exponer
# el resto del repo (backend/Android nativo/iOS nativo) al deploy de Vercel.
set -e
mkdir -p landing/app/css landing/app/js landing/app/icons
cp mobile/index.html mobile/manifest.json mobile/service-worker.js landing/app/
cp mobile/css/estilos.css landing/app/css/
cp mobile/js/seguro.js mobile/js/nucleo.js mobile/js/licencia.js mobile/js/app.js landing/app/js/
cp mobile/icons/*.png landing/app/icons/

# Vercel sirve /app/ con trailingSlash=false, redirige a /app y ahí los links
# relativos (css/, js/) se resuelven contra la raiz -> 404 -> demo sin estilo.
# Inyectamos <base href="/app/"> SOLO en la copia web (no en mobile/ original,
# que usa rutas relativas para la app descargada file://) para que TODO resuelva
# bien sin importar la barra final.
sed -i 's#<head>#<head>\n<base href="/app/">#' landing/app/index.html
