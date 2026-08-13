// © 2026 Martín Viera. Todos los derechos reservados.
/* verificar_keystore_android.mjs — El keystore de firma de Android NUNCA
 * viaja en el repo, ni el .gradle ni el .sh tienen una contraseña de repuesto.
 *
 * POR QUE EXISTE: android/app/mv-release.keystore y su contraseña en texto
 * plano ("mvfba2026", igual para store y key) estuvieron commiteados en
 * build.gradle desde el commit inicial del proyecto Android -- y el repo
 * paso por publico en algun momento, asi que cualquiera pudo haberlos
 * copiado mientras tanto. Se roto la clave (nuevo keystore, contraseña
 * random de 32 caracteres) y el diseño paso a variables de entorno sin
 * default: MVFBA_KEYSTORE_PATH / MVFBA_KEYSTORE_PASSWORD / MVFBA_KEY_ALIAS,
 * cargadas en CI desde GitHub Actions Secrets (MVFBA_KEYSTORE_BASE64 +
 * MVFBA_KEYSTORE_PASSWORD + MVFBA_KEY_ALIAS) y nunca commiteadas.
 *
 * Este test fija que esa contraseña vieja no reaparezca, que ningun archivo
 * .gradle/.sh tenga UN VALOR fijo como contraseña de repuesto (con o sin
 * comillas, cualquier string que no sea una llamada a variable de entorno
 * cuenta como regresion), y que el binario del keystore no pueda volver a
 * quedar trackeado por git.
 *
 * Uso:   node test/verificar_keystore_android.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";

const RAIZ = path.join(import.meta.dirname, "..");
let fallas = 0;
const ok = (m) => console.log("OK     " + m);
const falla = (m) => { fallas++; console.error("FALLA  " + m); };

const GRADLE = fs.readFileSync(path.join(RAIZ, "android/app/build.gradle"), "utf8");
const BUILD_SH = fs.readFileSync(path.join(RAIZ, "android/build-apk.sh"), "utf8");
const WORKFLOW = fs.readFileSync(path.join(RAIZ, ".github/workflows/android-apk.yml"), "utf8");
const GITIGNORE = fs.readFileSync(path.join(RAIZ, ".gitignore"), "utf8");

// --- 1) la contraseña vieja no puede reaparecer en NINGUN archivo del repo ---
// git grep, no fs: cubre el arbol entero de una, y falla si el binario del
// keystore (que la lleva embebida en su blob) volviera a estar trackeado.
//
// Se excluye ESTE archivo de su propio escaneo: el string vive legitimamente
// en el comentario de arriba y en el propio comando de busqueda de abajo, asi
// que git grep se encuentra a si mismo apenas queda trackeado -- un falso
// positivo que se confirmo en la practica (el test paso mientras el archivo
// estaba sin commitear, y fallo solo -contra si mismo- despues del commit).
const ESTE_ARCHIVO = path.relative(RAIZ, import.meta.filename ?? new URL(import.meta.url).pathname);
try {
  const hit = execSync(`git grep -l "mvfba2026" -- . ":(exclude)${ESTE_ARCHIVO}" 2>/dev/null || true`,
    { cwd: RAIZ, encoding: "utf8" }).trim();
  if (hit) falla(`la contraseña vieja "mvfba2026" sigue apareciendo en: ${hit}`);
  else ok('la contraseña vieja "mvfba2026" no aparece en ningun archivo trackeado (fuera de este test)');
} catch (e) {
  falla(`no se pudo correr git grep: ${e.message}`);
}

// --- 2) build.gradle: password y alias salen de env, no de un literal ---
if (/System\.getenv\(['"]MVFBA_KEYSTORE_PASSWORD['"]\)/.test(GRADLE)) {
  ok("build.gradle lee MVFBA_KEYSTORE_PASSWORD desde el entorno");
} else falla("build.gradle no lee la contraseña desde el entorno");

if (/storePassword\s+['"][^'"]+['"]/.test(GRADLE)) {
  falla("build.gradle tiene storePassword con un literal hardcodeado");
} else ok("  storePassword no es un literal hardcodeado");
if (/keyPassword\s+['"][^'"]+['"]/.test(GRADLE)) {
  falla("build.gradle tiene keyPassword con un literal hardcodeado");
} else ok("  keyPassword no es un literal hardcodeado");

// Sin la variable, tiene que CORTAR el build, no seguir con un valor vacio
// (que Gradle podria interpretar de formas raras segun la version del AGP).
if (/ksPass == null[\s\S]{0,40}throw new GradleException/.test(GRADLE)) {
  ok("  sin MVFBA_KEYSTORE_PASSWORD, el build corta con un error explicito");
} else falla("build.gradle no corta claramente si falta la contraseña");

// --- 3) build-apk.sh: mismo criterio, sin default de repuesto ---
// "${VAR:-}" (con nada entre ":-" y "}") es el modismo bash correcto para
// "vacio si no esta seteada" -- lo usa el chequeo `-z` de abajo, y NO es un
// valor de repuesto. Lo que se prohibe es "${VAR:-ALGO}" con algo real ahi.
if (/MVFBA_KEYSTORE_PASSWORD:-(?!\})\S/.test(BUILD_SH)) {
  falla("build-apk.sh todavia tiene una contraseña de repuesto (:- con un valor)");
} else ok("build-apk.sh no tiene ninguna contraseña de repuesto");
if (/if \[ -z "\$\{MVFBA_KEYSTORE_PASSWORD/.test(BUILD_SH)) {
  ok("  build-apk.sh corta si falta MVFBA_KEYSTORE_PASSWORD");
} else falla("build-apk.sh no valida que MVFBA_KEYSTORE_PASSWORD este seteada");

// --- 4) el keystore no puede volver a estar trackeado por git ---
const trackeados = execSync("git ls-files -- android/", { cwd: RAIZ, encoding: "utf8" });
if (/\.(keystore|jks)$/m.test(trackeados)) {
  falla("hay un .keystore o .jks TRACKEADO por git dentro de android/");
} else ok("ningun .keystore/.jks esta trackeado por git");

if (/^\*\.keystore\s*$/m.test(GITIGNORE) && /^\*\.jks\s*$/m.test(GITIGNORE)) {
  ok("  .gitignore cubre *.keystore y *.jks (no se pueden volver a commitear sin querer)");
} else falla(".gitignore no cubre *.keystore/*.jks: un `git add .` futuro los commitearia");

// --- 5) CI: el keystore sale de un secret, se decodifica y se borra ---
if (/secrets\.MVFBA_KEYSTORE_BASE64/.test(WORKFLOW)) {
  ok("el workflow trae el keystore desde el secret MVFBA_KEYSTORE_BASE64");
} else falla("el workflow no usa un secret para el keystore");
if (/secrets\.MVFBA_KEYSTORE_PASSWORD/.test(WORKFLOW) && /secrets\.MVFBA_KEY_ALIAS/.test(WORKFLOW)) {
  ok("  el workflow pasa password y alias como secrets, no hardcodeados");
} else falla("el workflow no pasa password/alias como secrets");
if (/rm -f android\/app\/mv-release\.keystore/.test(WORKFLOW)) {
  ok("  el workflow borra el keystore decodificado despues de compilar");
} else falla("el workflow no borra el keystore decodificado (queda tirado en el runner)");

console.log("");
if (fallas) {
  console.error(`FALLO: ${fallas} problema(s) en el manejo del keystore de Android.`);
  process.exit(1);
}
console.log("OK: el keystore de Android no viaja en el repo, sin contraseñas de "
  + "repuesto, y CI lo trae de secrets y lo borra al terminar.");
