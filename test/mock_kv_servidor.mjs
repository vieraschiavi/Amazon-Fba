/* mock_kv_servidor.mjs — Emulador MINIMO de la API REST de Upstash/Vercel KV,
 * para que los tests ejerciten api/_almacen.js, api/_seguridad.js y
 * api/_creditosia.js TAL CUAL corren en produccion (mismo fetch, mismo
 * parseo de respuesta) en vez de mockear esos modulos.
 *
 * Implementa solo los comandos que _almacen.js usa: get, set (con EX
 * opcional), lpush, ltrim, lrange. Suficiente para los tests de este repo,
 * no para uso general.
 */
import http from "node:http";

export function iniciarMockKv() {
  const datos = new Map();      // clave -> { valor, expiraEn (ms epoch) | null }
  const listas = new Map();     // clave -> array de strings (orden lpush)

  function vigente(clave) {
    const e = datos.get(clave);
    if (!e) return null;
    if (e.expiraEn && Date.now() > e.expiraEn) { datos.delete(clave); return null; }
    return e.valor;
  }

  const server = http.createServer((req, res) => {
    const partes = decodeURIComponent(req.url.slice(1)).split("/");
    const [cmd, ...args] = partes;
    let resultado = null;
    try {
      if (cmd === "get") {
        resultado = vigente(args[0]);
      } else if (cmd === "set") {
        const [clave, valor, exFlag, ttl] = args;
        const expiraEn = exFlag === "EX" && ttl ? Date.now() + Number(ttl) * 1000 : null;
        datos.set(clave, { valor, expiraEn });
        resultado = "OK";
      } else if (cmd === "lpush") {
        const [clave, valor] = args;
        const l = listas.get(clave) || [];
        l.unshift(valor);
        listas.set(clave, l);
        resultado = l.length;
      } else if (cmd === "ltrim") {
        const [clave, desde, hasta] = args;
        const l = listas.get(clave) || [];
        listas.set(clave, l.slice(Number(desde), Number(hasta) + 1));
        resultado = "OK";
      } else if (cmd === "lrange") {
        const [clave, desde, hasta] = args;
        const l = listas.get(clave) || [];
        const h = Number(hasta) === -1 ? l.length : Number(hasta) + 1;
        resultado = l.slice(Number(desde), h);
      } else {
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify({ error: "comando no soportado por el mock: " + cmd }));
        return;
      }
    } catch (e) {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: String(e) }));
      return;
    }
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ result: resultado }));
  });

  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolve({
        url: `http://127.0.0.1:${port}`,
        cerrar: () => new Promise((r) => server.close(r)),
        limpiar: () => { datos.clear(); listas.clear(); },
      });
    });
  });
}
