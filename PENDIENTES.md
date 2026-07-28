# Pendientes — MV FBA IA

> Estado verificado el **2026-07-25** contra producción (mvfbaia.com) y GitHub.
> Todo lo que queda pendiente depende de una **acción tuya** (credenciales o
> facturación): no hay código pendiente de escribir.

---

## Bloqueador 1 — La CI no puede compilar el instalador (cuota de GitHub Actions)

**Síntoma:** todos los jobs `build` fallan a los 2-5 segundos, con `runner_id: 0`
y sin runner asignado. Pasa tanto en `windows-latest` (Windows Installer) como en
`ubuntu-latest` (Android APK). Que fallen en segundos y sin runner significa que
**nunca llegaron a ejecutar nada**: no es un error del código.

**Consecuencia (importante):** el Release `pc-latest` quedó congelado en el
**5 de julio de 2026**. O sea, el instalador que se descarga desde la web **no
tiene** nada de lo que hicimos después:

- Python embebido (el cliente ya no necesita instalar Python) — PR #39
- API de Jungle Scout (BYOK) — PR #42
- Recomendación de nicho con Claude — PR #42
- Insights Jungle Scout: estacionalidad / share of voice / ventas por ASIN — PR #44
- Reabastecimiento (restock) — PR #45
- Herramientas: generador de URLs + Plan de Acción (POA) — PR #46
- Demo de 7 días — PR #47

**Cómo destrabarlo (elegí una):**
1. Esperar a que se renueve la cuota mensual de Actions.
2. Subir el límite en **GitHub → Settings → Billing → Actions → spending limit**.
3. Si no querés seguir gastando ahí, desactivar los workflows que no uses
   (Android APK) para que la cuota rinda solo para el instalador de Windows.

**Después de destrabar:** correr el workflow *Windows Installer (EXE)* (se dispara
solo con cualquier push a `*.py`, `agents/**`, `core/**`, `data/**`, `frontend/**`,
`installer/**`, o a mano desde Actions → Run workflow) para que publique un
`pc-latest` actualizado.

**Cómo verificar que quedó bien:**
```bash
# la fecha de publicación tiene que ser posterior al 2026-07-25
curl -s https://api.github.com/repos/vieraschiavi/Amazon-Fba/releases/tags/pc-latest \
  | grep -E '"published_at"|"name"'
```

---

## Bloqueador 2 — La descarga del instalador da 401 (`GITHUB_RELEASE_TOKEN` inválido)

**Síntoma actual en producción:**
```bash
curl "https://mvfbaia.com/api/descarga?demo=1"
# {"error":"descarga_no_disponible","motivo":"release_no_encontrado","status":401}
```

Ese `status: 401` es la respuesta de GitHub: el token existe en Vercel pero está
**vencido, mal copiado o sin el permiso correcto**. (Si faltara el token, el
`motivo` diría `sin_token`.)

**Por qué hace falta un token:** el repo es privado, así que las URLs de descarga
de los Releases devuelven 404 a cualquiera que no esté autenticado.
`api/_release.js` resuelve la descarga server-side con este token.

**Pasos exactos:**
1. GitHub → **Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token**.
2. **Repository access:** *Only select repositories* → `vieraschiavi/Amazon-Fba`.
3. **Permissions → Repository permissions → Contents: Read-only**.
   (Con eso alcanza; no le des nada más.)
4. Copiar el token (se muestra una sola vez).
5. Vercel → proyecto `amazon-fba` → **Settings → Environment Variables** →
   `GITHUB_RELEASE_TOKEN` = el token nuevo (Production).
6. **Deployments → (el de Production) → ⋯ → Redeploy.**
   ⚠️ Guardar la variable **no** alcanza: las funciones siguen corriendo con las
   variables horneadas en el último build. Sin redeploy no cambia nada.

**Cómo verificar que quedó bien:**
```bash
curl -sS -o /dev/null -w '%{http_code}\n' "https://mvfbaia.com/api/descarga?demo=1"
# 302  -> OK (redirige al instalador)
# 502  -> seguí mirando "motivo" en el body
```

---

## Bloqueador 3 — El instalador "owner" nunca se compiló

No existe el Release `owner-latest`. El build owner (el instalador tuyo, que
arranca ya activado como Pro, sin pagar ni activar nada a mano) **nunca se corrió**.

Depende del Bloqueador 1 (necesita la CI andando) y además de dos secrets:

1. GitHub → **Settings → Secrets and variables → Actions**:
   - `OWNER_LICENSE_EMAIL` = tu email (el mismo que `OWNER_EMAIL` en Vercel)
   - `OWNER_LICENSE_KEY` = la clave que devuelve el endpoint de dueño (ver abajo)
2. Actions → **Windows Installer (EXE) → Run workflow** → marcar **owner: true**.
3. Se publica en el Release `owner-latest` (nunca pisa `pc-latest`, que es el de
   los clientes).

**Para obtener tu clave de licencia de dueño** (esto ya funciona hoy):
```bash
curl -H "x-mv-app: mvfba-web-1" \
  "https://mvfbaia.com/api/licencia?dueno=1&email=TU_EMAIL"
```

---

## Pendiente de producto — la app está solo a medias en inglés y portugués

Salió a la luz al arreglar las capturas del video: **el programa no está traducido
del todo**. Lo que sí cambia de idioma es el "marco" (menú lateral, títulos de
pantalla, botones, badge de la demo, selector de idioma). Lo que **sigue en
español** aunque elijas EN o PT:

- Etiquetas de los formularios y de los KPI: `COSTO UNITARIO`, `FLETE UNITARIO`,
  `ARANCEL`, `PREP`, `PRECIO COMPETENCIA`, `PRECIO SUGERIDO`, `MARGEN`,
  `NOMBRE DEL PRODUCTO`, `TECHO DEMANDA`… (~104 textos fijos entre las 6
  pantallas que muestra el video).
- Encabezados de varias tablas.
- Textos que arma el backend: `competitivo (-5% vs lider)`, `costo desembarcado`,
  el semáforo `VERDE/AMARILLO/ROJO`, etc.
- **La PWA / app de celular está prácticamente sin traducir**: solo cambian de
  idioma la pantalla de licencia y poco más; el resto (Resumen ejecutivo,
  Facturación, Accesos rápidos, la barra de navegación) está siempre en español.

Consecuencia comercial: alguien que compra desde la web en inglés recibe un
programa mayormente en español. Traducirlo es un trabajo aparte y grande, porque
toca el frontend (React) y también textos que genera el backend en Python.

## Ya verificado y funcionando (no tocar)

| Cosa | Estado |
|---|---|
| `OWNER_EMAIL` en Vercel | ✅ Configurado. El endpoint de dueño devuelve licencia Pro válida. |
| Demo de 7 días — reloj real | ✅ `DIAS_DEMO = 7` en `core/licencia.py` y `mobile/js/licencia.js`. |
| Demo de 7 días — web | ✅ 13 menciones en ES/EN/PT en producción, 0 residuos de "3 días". |
| Demo de 7 días — audios | ✅ Los 3 `.mp3` en producción dicen "siete días / seven days / sete dias" (checksums idénticos a los locales). |
| Escenas del video sincronizadas | ✅ 9 escenas × 3 idiomas verificadas tras regenerar el audio. |
| Banco de tests | ✅ 47/47. |
| Flujo e2e en modo demo | ✅ 32/32 checks, datos correlacionados entre todas las pestañas. |

---

## Notas para retomar

- El repo es **privado**: cualquier descarga pública de Releases necesita pasar
  por `api/descarga.js` + `api/_release.js` con el token.
- `landing/app/` **no se commitea**: lo genera `scripts/vercel-build.sh` copiando
  `mobile/`. Si tocás la PWA, editá `mobile/` (es la fuente de verdad).
- `DOMINIO = "MV-Amazon-Fba"` y `LICENCIA_SECRETO` **no se cambian nunca**:
  cambiarlos invalida las licencias ya vendidas.
- Las dos fuentes de verdad del reloj de la demo son `core/licencia.py` (PC) y
  `mobile/js/licencia.js` (PWA/Android). Si cambia la duración, hay que ajustar
  también la ventana del mail recordatorio en `api/cron-recordatorio-demo.js`.
