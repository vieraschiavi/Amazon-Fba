// service-worker.js — cache del "shell" de la app (HTML/CSS/JS/iconos) para que
// abra instantanea y funcione OFFLINE por completo. El motor de negocio corre
// en el telefono (nucleo.js) y los datos viven en localStorage, asi que no hay
// nada que pedirle a ninguna PC: la app entera funciona sin red.
//
// v3 — FIX de la demo "rota" en celulares que ya la habian visitado: la v2 era
// cache-first con version fija, asi que un telefono que instalo el SW una vez
// quedaba sirviendo la app VIEJA para siempre (los deploys nuevos nunca le
// llegaban -> "da error" con bugs ya corregidos). Ahora:
//   - El HTML (navegaciones) va RED-PRIMERO: si hay internet, siempre se ve la
//     version publicada; sin internet, cae a la copia cacheada (sigue offline).
//   - CSS/JS/iconos: cache-first PERO se refrescan en segundo plano en cada
//     visita (stale-while-revalidate), asi la proxima apertura ya esta al dia.
//   - El bump de version purga el cache viejo en cuanto el telefono revisita.
// v4 — dos cosas:
//   - FIX: js/seguro.js se cargaba en index.html pero NO estaba en esta lista,
//     asi que un arranque EN FRIO sin conexion lo pedia a la red, fallaba, y
//     escapar() quedaba sin definir -> la app rompia entera al primer render.
//     Lo cubre test/verificar_sw_precache.mjs para que no vuelva a pasar.
//   - El bump purga el cache viejo: nucleo.js suma la estimacion por BSR.
const CACHE = "mv-fba-ia-shell-v4";
const SHELL = [
  "./",
  "./index.html",
  "./css/estilos.css",
  "./js/seguro.js",
  "./js/nucleo.js",
  "./js/licencia.js",
  "./js/app.js",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

self.addEventListener("install", (ev) => {
  ev.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (ev) => {
  const url = new URL(ev.request.url);
  // Solo el shell estatico (mismo origen que este SW) pasa por el cache;
  // cualquier llamada a la API (otro origen/puerto) va siempre a la red.
  if (url.origin !== self.location.origin) return;
  if (ev.request.method !== "GET") return;

  // HTML / navegaciones: red-primero (app siempre actualizada), cache si no hay red.
  if (ev.request.mode === "navigate" || ev.request.destination === "document") {
    ev.respondWith(
      fetch(ev.request)
        .then((resp) => {
          const copia = resp.clone();
          caches.open(CACHE).then((c) => c.put(ev.request, copia));
          return resp;
        })
        .catch(() => caches.match(ev.request).then((c) => c || caches.match("./index.html")))
    );
    return;
  }

  // Assets: cache-first con refresco en segundo plano (stale-while-revalidate).
  ev.respondWith(
    caches.match(ev.request).then((cached) => {
      const refresco = fetch(ev.request)
        .then((resp) => {
          if (resp && resp.ok) {
            const copia = resp.clone();
            caches.open(CACHE).then((c) => c.put(ev.request, copia));
          }
          return resp;
        })
        .catch(() => cached);
      return cached || refresco;
    })
  );
});
