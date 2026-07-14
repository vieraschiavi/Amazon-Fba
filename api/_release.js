// api/_release.js — Resuelve la URL real de descarga de un asset de un
// Release de GitHub. El repo es PRIVADO: el link "publico" de un Release
// (github.com/.../releases/download/...) le da 404 a cualquier visitante
// anonimo aunque el Release este publicado -- GitHub solo sirve esos links
// sin login en repos publicos. Por eso nunca se redirige ahi directo.
//
// En cambio, se pide el asset server-side con un token de solo lectura y se
// sigue el redirect FIRMADO que da la API (objects.githubusercontent.com),
// que si es descargable sin login por unos minutos. El repo sigue privado;
// el token nunca se expone al cliente.
const OWNER = "vieraschiavi";
const REPO = "Amazon-Fba";

export function releaseConfigurado() {
  return Boolean(process.env.GITHUB_RELEASE_TOKEN);
}

// Devuelve {url, motivo} en vez de solo la URL: "motivo" nunca expone el
// token, pero permite diagnosticar por que fallo (falta el token, el
// release/asset no aparecio, o GitHub no devolvio el redirect esperado)
// sin tener que mirar logs de Vercel.
export async function resolverDescargaRelease(tag, nombreAsset) {
  const token = String(process.env.GITHUB_RELEASE_TOKEN || "").trim();
  if (!token) return { url: null, motivo: "sin_token" };
  const headers = { authorization: `Bearer ${token}`, "user-agent": "mvfba-descargas" };

  const rel = await fetch(`https://api.github.com/repos/${OWNER}/${REPO}/releases/tags/${encodeURIComponent(tag)}`, {
    headers: { ...headers, accept: "application/vnd.github+json" },
  });
  if (!rel.ok) return { url: null, motivo: "release_no_encontrado", status: rel.status };
  const datos = await rel.json();
  const asset = (datos.assets || []).find((a) => a.name === nombreAsset);
  if (!asset) return { url: null, motivo: "asset_no_encontrado" };

  const resp = await fetch(asset.url, {
    headers: { ...headers, accept: "application/octet-stream" },
    redirect: "manual",
  });
  if (resp.status >= 300 && resp.status < 400) return { url: resp.headers.get("location"), motivo: "ok" };
  return { url: null, motivo: "sin_redirect", status: resp.status };
}
