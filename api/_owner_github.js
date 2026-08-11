// api/_owner_github.js — Autoriza el build OWNER probando acceso al repo privado.
//
// POR QUE ASI
// -----------
// La licencia de dueño la pide el workflow de GitHub para hornearla dentro del
// instalador interno. La pregunta es como distingue el servidor "esto lo pide mi
// build" de "esto lo pide cualquiera desde la web".
//
// Pedirle al dueño que configure un token a mano en dos lados era friccion sin
// seguridad real: quien puede correr el workflow YA tiene acceso total al repo
// privado. Asi que la autorizacion ES el acceso al repo.
//
// El workflow manda el GITHUB_TOKEN que Actions le da solo (efimero, con alcance
// a este repo). Aca se verifica contra la API de GitHub: si ese token puede leer
// el repo PRIVADO, quien llama es el dueño o alguien a quien el dueño le dio
// acceso. Nadie desde la web tiene un token asi.
//
// Resultado: cero configuracion, y el camino publico sigue cerrado.
//
// El prefijo "_" hace que Vercel NO trate este archivo como una ruta.

// Repo FIJO, escrito aca y nunca tomado del request: si viniera del cliente,
// cualquiera apuntaria a un repo suyo, sacaria un 200 y se colaria.
const REPO_ESPERADO = "vieraschiavi/Amazon-Fba";

/**
 * ¿El token prueba acceso de lectura al repo privado del producto?
 * Devuelve false ante cualquier duda (falla cerrado). Nunca lanza.
 */
export async function accesoAlRepoValido(token, fetchImpl = fetch) {
  const limpio = String(token || "").trim();
  if (!limpio) return false;
  try {
    const r = await fetchImpl(`https://api.github.com/repos/${REPO_ESPERADO}`, {
      headers: {
        authorization: `Bearer ${limpio}`,
        accept: "application/vnd.github+json",
        "user-agent": "mvfba-owner-build",
      },
    });
    if (!r.ok) return false;
    const d = await r.json();
    // Que sea EXACTAMENTE este repo y no otro homonimo. Si no, nada mas importa.
    if (!d || d.full_name !== REPO_ESPERADO) return false;

    // Repo PRIVADO: poder leerlo YA prueba acceso, porque nadie mas puede.
    if (d.private === true) return true;

    // Repo PUBLICO: leerlo no prueba absolutamente nada -- lo lee cualquiera,
    // sin token siquiera. Antes esto devolvia false y listo, lo que dejaba el
    // build owner IMPOSIBLE de correr mientras el repo estuviera publico (hay
    // razones para tenerlo asi: los repos publicos tienen minutos de Actions
    // ilimitados). Obligaba a togglear la visibilidad a mano en cada build, y
    // peor: si alguien lo hacia publico y se olvidaba, el build owner fallaba
    // con un 403 que no explicaba por que.
    //
    // Lo que SI prueba ser el dueño, con el repo publico o privado, es tener
    // permiso de ESCRITURA. GitHub devuelve "permissions" cuando la llamada va
    // autenticada: a un desconocido con un token propio le da
    // {pull:true, push:false, admin:false} sobre un repo publico -- puede
    // leerlo, no tocarlo. Al dueño (y al GITHUB_TOKEN efimero del workflow,
    // que corre con contents:write) le da push/admin en true.
    //
    // O sea: la barrera sigue siendo "tener acceso de escritura al repo", que
    // es exactamente el mismo grupo de gente que puede correr el workflow. No
    // se abre nada; se deja de depender de un detalle (la visibilidad) que no
    // tiene por que estar atado a esto.
    const permisos = d.permissions || {};
    return permisos.admin === true
        || permisos.maintain === true
        || permisos.push === true;
  } catch (_) {
    return false;   // sin red, token invalido, respuesta rara: no autoriza
  }
}

export const REPO_OWNER_ESPERADO = REPO_ESPERADO;
