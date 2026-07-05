// service-worker.js — cache del "shell" de la app (HTML/CSS/JS/iconos) para que
// abra instantanea y funcione OFFLINE por completo. El motor de negocio corre
// en el telefono (nucleo.js) y los datos viven en localStorage, asi que no hay
// nada que pedirle a ninguna PC: la app entera funciona sin red.
const CACHE = "mv-fba-ia-shell-v2";
const SHELL = [
  "./",
  "./index.html",
  "./css/estilos.css",
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
  // Solo el shell estatico (mismo origen que este SW) se sirve de cache;
  // cualquier llamada a la API (otro origen/puerto) va siempre a la red.
  if (url.origin !== self.location.origin) return;
  ev.respondWith(
    caches.match(ev.request).then((cached) => cached || fetch(ev.request))
  );
});
