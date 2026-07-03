// service-worker.js — cache del "shell" de la app (HTML/CSS/JS/iconos) para que
// abra instantaneo y funcione offline en modo lectura de la ultima pantalla.
// Los datos (KPIs, portafolio, etc.) siempre se piden en vivo a la API: nunca
// se cachean, para no mostrar numeros del negocio desactualizados.
const CACHE = "mv-fba-ia-shell-v1";
const SHELL = [
  "./",
  "./index.html",
  "./css/estilos.css",
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
  // Solo el shell estatico (mismo origen que este SW) se sirve de cache;
  // cualquier llamada a la API (otro origen/puerto) va siempre a la red.
  if (url.origin !== self.location.origin) return;
  ev.respondWith(
    caches.match(ev.request).then((cached) => cached || fetch(ev.request))
  );
});
