#!/bin/sh
# Copia la PWA (mobile/, solo HTML/CSS/JS) dentro de landing/app/ para que la
# landing pueda linkear una demo real y usable ("Probar demo"), sin exponer
# el resto del repo (backend/Android nativo/iOS nativo) al deploy de Vercel.
set -e
mkdir -p landing/app/css landing/app/js landing/app/icons
cp mobile/index.html mobile/manifest.json mobile/service-worker.js landing/app/
cp mobile/css/estilos.css landing/app/css/
cp mobile/js/nucleo.js mobile/js/licencia.js mobile/js/app.js landing/app/js/
cp mobile/icons/*.png landing/app/icons/
