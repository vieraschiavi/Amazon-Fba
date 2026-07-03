# Conectar el sistema (paso a paso)

La via mas simple: abri el panel (`INICIAR.bat`) → pestaña **Config** → **Claves de API**.
Los campos son tipo contraseña, se guardan en `.env` local (fuera de git, con permisos
restringidos) y nunca se muestran completos.

Alternativa manual: copiá `.env.example` a `.env` (o corré `CONECTAR.bat`, que lo crea solo
la primera vez) y pegá las claves que tengas. Después corré **`CONECTAR.bat`** para ver
verde/rojo en cada una.

El sistema funciona sin ninguna clave (listing offline, alertas en dry-run, keywords por CSV).
Cada conexión suma capacidad; ninguna es obligatoria salvo que quieras ese dato puntual.

## 1) Keepa (precio + BSR programatico) — paso humano, no lo puedo hacer por vos
1. Entra a keepa.com → Register → verifica el email.
2. La API **no tiene free trial**: hay que suscribir el plan de **19 EUR/mes** (o 189 EUR/año,
   ahorra 17%). Login → tu usuario (arriba a la derecha) → datos de facturacion → Subscribe.
   Paga con tarjeta o Google Pay; factura en euros (puede haber recargo por conversion).
3. Logueado, anda a la pagina **Keepa API** (keepa.com/#!api) y copia la
   **"Private API access key"** (es unica de tu cuenta).
4. Pegala en `.env`:  `KEEPA_API_KEY=tu_clave`   (US ya queda en `KEEPA_DOMAIN=1`).
5. Verifica:  `CONECTAR.bat`  (o `python test_conexiones.py --asin B08XXXXX` para traer 1
   producto real; eso gasta 1 token). Con el plan basico tenes 1 token/min, y los tokens
   expiran a los 60 min, asi que el sistema consulta por evento, no en bucle.

## 2) Anthropic (Claude redacta el listing) — opcional
1. console.anthropic.com → API Keys → Create Key. Copia la clave `sk-ant-...`.
2. `.env`:  `ANTHROPIC_API_KEY=sk-ant-...`
3. Sin esta clave, el listing se genera offline (plantillas con tus keywords); no es error.

## 3) Gmail / SMTP (alertas reales por email) — opcional
1. La cuenta de Gmail necesita **verificacion en 2 pasos** activada.
2. Crea un **App Password** (myaccount.google.com → Seguridad → Contraseñas de aplicaciones).
   Es una clave de 16 caracteres distinta de tu contraseña normal.
3. `.env`:
   `SMTP_USER=tucuenta@gmail.com`
   `SMTP_PASS=app_password_de_16_caracteres`
   `ALERT_TO=vieraschiavi@gmail.com`
4. Sin esto, las alertas quedan en dry-run (se registran en la tabla, no se envian).

## 4) Cerebro CSV (keywords de Helium 10) — opcional
1. En Helium 10 Cerebro, corre tu busqueda y toca **Export Data**.
2. Deja el `.csv` en `data/cerebro_exports/` (o subilo desde la pestaña Investigacion).
3. Helium 10 no expone Cerebro por API en Platinum: el CSV es la via sostenible.

## Verificar todo
`CONECTAR.bat`  → valida de verdad: Keepa (endpoint /token, no gasta), Anthropic (/models),
SMTP (login real) y lectura del CSV. Tambien tenes el boton **Probar conexiones** en la
pestaña Config del panel.
