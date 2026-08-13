// © 2026 Martín Viera. Todos los derechos reservados.
/* seguro.js — Unica funcion de escape de HTML de la PWA.
   Todo dato que llega de Amazon (Keepa/Jungle Scout), del usuario o de la
   propia API y termina insertado en el DOM via innerHTML (contenido O
   atributo, ej. value="${escapar(d.nombre)}" en el modal de producto) pasa
   por ACA. Un solo lugar, un solo test de regresion (verificar_escapar.js).

   Escapa & < > " ' -- las comillas son las que importan de verdad: sin ellas,
   un titulo de Amazon tan comun como 'Bamboo Set 10" Kitchen' corta el
   atributo value="..." y deja lugar para colgar un handler (onfocus=...). */
function escapar(t) {
  return String(t == null ? "" : t)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

if (typeof module !== "undefined" && module.exports) module.exports = { escapar };
