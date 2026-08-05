/* verificar_instalador.mjs — El instalador de Windows tiene que ser
 * distribuible tal cual: sin documentacion interna adentro, con metadatos
 * profesionales, dejando elegir carpeta y desinstalando sin dejar residuos.
 *
 * POR QUE EXISTE: el .iss empaquetaba "..\*.md" en bloque, asi que el
 * instalador que compra un cliente se llevaba CLAUDE.md (instrucciones
 * internas de desarrollo) y PENDIENTES.md (bloqueadores internos, nombres de
 * secrets, mapa de la infraestructura y el endpoint de licencia de dueño).
 * Nadie lo noto porque compilaba perfecto: un wildcard que crece solo no
 * rompe nada, solo filtra de mas.
 *
 * Tambien fija que el build OWNER no pueda pisar el Release de los clientes,
 * que es la clase de error que se paga caro una sola vez.
 *
 * Uso:   node test/verificar_instalador.mjs
 */
import fs from "node:fs";
import path from "node:path";

const RAIZ = path.join(import.meta.dirname, "..");
// Inno permite cortar una entrada en varias lineas terminandolas en "\". Se
// re-unen ANTES de analizar: si no, una entrada partida se lee como dos lineas
// sueltas y los chequeos sobre ella (p.ej. su "Check:") dan falso negativo.
const ISS = fs.readFileSync(
  path.join(RAIZ, "installer/MV_Amazon_FBA_IA.iss"), "utf8")
  .replace(/\\[ \t]*\r?\n[ \t]*/g, " ");
const WF = fs.readFileSync(
  path.join(RAIZ, ".github/workflows/windows-installer.yml"), "utf8");

const fallos = [];
const ok = (m) => console.log("OK     " + m);
const falla = (m) => { fallos.push(m); console.log("FALLA  " + m); };

// --- 1) nada interno viaja adentro del instalador ---
const lineasFiles = ISS.split("\n").filter((l) => /^\s*Source:/i.test(l));
if (!lineasFiles.length) falla("no encontre ninguna linea Source: en [Files]");
else ok(`[Files] declara ${lineasFiles.length} origen(es)`);

// Un wildcard de .md vuelve a arrastrar lo interno apenas alguien cree un .md
// nuevo en la raiz, asi que se prohibe el patron, no solo los dos archivos.
const wildcardMd = lineasFiles.filter((l) => /\\\*\.md/i.test(l));
if (wildcardMd.length) {
  falla('[Files] usa el wildcard "..\\*.md": cualquier .md interno nuevo se ' +
        "filtraria al instalador. Listar los .md del cliente uno por uno.");
} else ok('[Files] no usa wildcard de .md (los documentos se listan explicitos)');

for (const interno of ["CLAUDE.md", "PENDIENTES.md"]) {
  if (lineasFiles.some((l) => l.includes(interno))) {
    falla(`[Files] empaqueta ${interno}, que es documentacion INTERNA`);
  } else ok(`  ${interno} no se distribuye`);
}
for (const cliente of ["README.md", "CONEXIONES.md"]) {
  if (lineasFiles.some((l) => l.includes(cliente))) ok(`  ${cliente} si se distribuye`);
  else falla(`[Files] ya no incluye ${cliente}, que si es documentacion del cliente`);
}

// --- 2) el .exe tiene metadatos (Propiedades > Detalles en Windows) ---
for (const clave of ["VersionInfoVersion", "VersionInfoProductName",
                     "VersionInfoCompany", "VersionInfoDescription"]) {
  if (new RegExp(`^\\s*${clave}=`, "im").test(ISS)) ok(`  ${clave} definido`);
  else falla(`falta ${clave}: el instalador queda sin metadatos en Windows`);
}

// --- 3) el usuario elige donde instalar ---
if (/^\s*DefaultDirName=\{code:CarpetaPorDefecto\}/im.test(ISS)) {
  ok("DefaultDirName se resuelve en [Code] (no usa {autopf}, que abortaba)");
} else falla("DefaultDirName ya no usa {code:CarpetaPorDefecto}");
if (/^\s*DisableDirPage=no/im.test(ISS)) ok("la pagina de elegir carpeta SIEMPRE se muestra");
else falla("DisableDirPage deberia ser 'no': el usuario tiene que poder elegir disco/carpeta");
if (/^\s*PrivilegesRequiredOverridesAllowed=dialog/im.test(ISS)) {
  ok("deja elegir instalar para todos los usuarios o solo para mi");
} else falla("falta PrivilegesRequiredOverridesAllowed=dialog");

// --- 4) la desinstalacion no deja residuos ---
// runtime\ es el caso critico: Python escribe __pycache__ dentro de
// site-packages al usar el programa, y eso NO esta en [Files].
for (const dir of ["runtime", "frontend"]) {
  const re = new RegExp(`DelTree\\(AppDir \\+ '\\\\${dir}', True, True, True\\)`);
  if (re.test(ISS)) ok(`  la desinstalacion borra ${dir}\\ completo (sin .pyc huerfanos)`);
  else falla(`la desinstalacion no borra ${dir}\\ entero: quedan residuos tras usar el programa`);
}
// pero NUNCA un borrado en bloque de {app}: el usuario elige la carpeta.
if (/DelTree\(AppDir, True, True, True\)/.test(ISS)) {
  falla("DelTree(AppDir, True, True, True) borraria TODO el destino elegido " +
        "por el usuario, incluso archivos ajenos. Usar subcarpetas explicitas.");
} else ok("no hay borrado en bloque de {app} (no se lleva puesto nada ajeno)");
if (/SuppressibleMsgBox/.test(ISS)) {
  ok("la pregunta de borrar datos usa SuppressibleMsgBox (no cuelga en silencioso)");
} else falla("InitializeUninstall deberia usar SuppressibleMsgBox");

// --- 5) los 3 perfiles: owner / cliente pago / demo ---
// El .iss es el MISMO para los tres: owner se distingue por traer la licencia
// adentro, y demo/pago se distinguen recien en runtime (reloj de 7 dias).
const lineaOwner = lineasFiles.find((l) => l.includes("owner_licencia.json"));
if (!lineaOwner) falla("[Files] no contempla owner_licencia.json (build owner)");
else if (!/skipifsourcedoesntexist/i.test(lineaOwner)) {
  falla("owner_licencia.json sin skipifsourcedoesntexist: el build de CLIENTES " +
        "no compilaria (o peor, exigiria el archivo del dueño)");
} else ok("owner_licencia.json es opcional: el build de clientes compila sin el");

// --- 6) el build owner NO puede pisar el Release de los clientes ---
const bloques = WF.split(/\n(?=      - name: )/);
const pubClientes = bloques.find((b) => /tag_name: pc-latest/.test(b));
const pubOwner = bloques.find((b) => /tag_name: owner-latest/.test(b));
if (!pubClientes) falla("el workflow ya no publica el Release pc-latest");
else if (/inputs\.owner != 'true'/.test(pubClientes)) {
  ok("pc-latest (clientes) se salta explicitamente en un build owner");
} else falla("pc-latest podria publicarse desde un build OWNER: pisaria a los clientes");
if (!pubOwner) falla("el workflow ya no publica el Release owner-latest");
else if (/inputs\.owner == 'true'/.test(pubOwner)) {
  ok("owner-latest solo se publica en un build owner");
} else falla("owner-latest se publicaria en un build normal");

// --- 7) la app tiene que abrir como PROGRAMA, no como pagina web ---
// Se abre con Electron, que trae su propio Chromium adentro. Antes se usaba
// pywebview sobre el runtime WebView2 de Edge, que es un componente del
// SISTEMA: si la maquina no lo tenia, la ventana no podia abrir y la app caia
// a mostrarse en el navegador -- el cliente veia "una web" en vez de un
// programa. Electron no depende de nada instalado.
if (/@electron\/packager/.test(WF)) ok("el CI empaqueta la app de Electron");
else falla("el CI no empaqueta Electron: el instalador no tendria la app de escritorio");

if (/electron-dist.*MV FBA IA-win32-x64/.test(WF)) {
  ok("el CI verifica que el empaquetado de Electron salga entero");
} else falla("el CI no verifica el resultado del empaquetado de Electron");

const bundleaElectron = lineasFiles.some((l) => /electron-dist/.test(l));
if (bundleaElectron) ok("el instalador empaqueta la app de Electron");
else falla("[Files] no incluye la app de Electron (electron-dist)");

// Todos los accesos directos y el "abrir ahora" tienen que ir al .exe de
// Electron, no al .vbs viejo que lanzaba un .bat oculto.
const lineasIcon = ISS.split("\n").filter((l) => /^\s*Name:\s*"\{(group|autodesktop)\}/i.test(l));
const principales = lineasIcon.filter((l) => !/modo navegador|Diagnostico|Verificar conexiones|Desinstalar/i.test(l));
if (!principales.length) falla("no encontre los accesos directos principales");
else {
  const malos = principales.filter((l) => !/desktop\\MV FBA IA\.exe/.test(l));
  if (malos.length) falla(`${malos.length} acceso(s) directo(s) principal(es) no apuntan al .exe de Electron`);
  else ok(`los ${principales.length} accesos directos principales abren el .exe de Electron`);
}
const runApp = ISS.split("\n").filter((l) => /^\s*Filename:/i.test(l))
  .find((l) => /postinstall/.test(l));
if (!runApp) falla("[Run] no tiene la opcion 'Abrir ahora' al terminar");
else if (!/desktop\\MV FBA IA\.exe/.test(runApp)) {
  falla("el 'Abrir ahora' del final no lanza el .exe de Electron");
} else ok("el 'Abrir ahora' del final lanza el .exe de Electron");

// La desinstalacion tiene que llevarse tambien desktop\ (Electron pesa ~200 MB)
if (/DelTree\(AppDir \+ '\\desktop', True, True, True\)/.test(ISS)) {
  ok("  la desinstalacion borra desktop\\ (la app de Electron)");
} else falla("la desinstalacion no borra desktop\\: quedarian ~200 MB de Electron");

// main.js: el motor Python tiene que apagarse SIEMPRE con la app.
const MAIN = fs.readFileSync(path.join(RAIZ, "electron/main.js"), "utf8");
for (const ev of ["window-all-closed", "before-quit"]) {
  if (new RegExp(`"${ev}"`).test(MAIN)) ok(`  main.js apaga el motor en ${ev}`);
  else falla(`main.js no apaga el motor en ${ev}: quedaria un uvicorn huerfano`);
}
if (/requestSingleInstanceLock/.test(MAIN)) {
  ok("  una sola instancia: dos clics no levantan dos motores sobre la misma base");
} else falla("main.js sin requestSingleInstanceLock");
if (/nodeIntegration:\s*false/.test(MAIN) && /contextIsolation:\s*true/.test(MAIN)) {
  ok("  la ventana no expone Node al contenido web");
} else falla("main.js deberia usar nodeIntegration:false + contextIsolation:true");

console.log("");
if (fallos.length) {
  console.error(`FALLO: ${fallos.length} problema(s) en el instalador.`);
  process.exit(1);
}
console.log("OK: el instalador no filtra documentacion interna, tiene metadatos, "
  + "deja elegir carpeta, abre la app de Electron, desinstala sin residuos y "
  + "separa owner de clientes.");
