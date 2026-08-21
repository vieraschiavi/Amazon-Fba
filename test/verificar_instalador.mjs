// © 2026 Martín Viera. Todos los derechos reservados.
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
if (/^\s*AlwaysShowDirOnReadyPage=yes/im.test(ISS)) {
  ok("la carpeta elegida se repite en la pagina final de confirmacion");
} else falla("falta AlwaysShowDirOnReadyPage=yes: el usuario no confirma donde instala");
// El default NO puede caer siempre en C:. En una maquina con C: chico y D:
// grande, proponer C: es el peor lugar: ahi va tambien %LOCALAPPDATA%, donde
// se guarda la base -- ya hubo un "database or disk is full" real por eso.
if (/function DiscoConEspacio/.test(ISS) && /Ord\('D'\) to Ord\('Z'\)/.test(ISS)) {
  ok("el destino por defecto busca un disco distinto de C: con espacio");
} else falla("el instalador volveria a proponer C: siempre como destino");
if (/DRIVE_FIXED\s*=\s*3/.test(ISS) && /GetDriveTypeW@kernel32\.dll/.test(ISS)) {
  ok("  solo considera discos internos (ni pendrive, ni red, ni CD)");
} else {
  falla("sin filtrar por DRIVE_FIXED el default podria caer en un pendrive o " +
        "una unidad de red: al desconectarse el programa queda roto");
}
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
  ok("owner-latest se publica en el build owner");
} else falla("owner-latest ya no se publicaria en un build owner");
// El dueño tiene que tener SIEMPRE un instalador propio fresco para probar el
// programa completo, sin depender de acordarse de lanzar el workflow a mano
// (que era el estado anterior: owner-latest no existia y INSTALAR_OWNER.bat
// abria un 404).
if (pubOwner && /refs\/heads\/main/.test(pubOwner)) {
  ok("owner-latest se republica solo en cada push a main");
} else falla("owner-latest solo saldria a mano: el dueño se queda sin instalador");

// --- 6b) el instalador de CLIENTES no puede salir pre-activado ---
// Garantia clave del build owner automatico: owner_licencia.json se escribe
// DESPUES de compilar y publicar el .exe de clientes. Si algun dia alguien
// reordena los pasos, el instalador que compra un cliente saldria con la
// licencia Pro del dueño adentro -- se regala el producto.
const posLic = WF.indexOf("Escribir licencia owner");
const posCompilaCliente = WF.indexOf("- name: Compilar instalador\n");
const posPubCliente = WF.indexOf("tag_name: pc-latest");
if (posLic < 0 || posCompilaCliente < 0 || posPubCliente < 0) {
  falla("no encuentro los pasos de compilar/publicar cliente y escribir la licencia owner");
} else if (posCompilaCliente < posLic && posPubCliente < posLic) {
  ok("la licencia owner se escribe DESPUES de compilar y publicar el de clientes");
} else {
  falla("owner_licencia.json se escribiria ANTES de compilar/publicar el instalador " +
        "de CLIENTES: saldria pre-activado como Pro (se regala el producto)");
}
// Y el .exe owner se compila en su propia carpeta para no pisar el de clientes.
if (/ISCC\.exe" \/O"\$salida"/.test(WF) && /installer\\Output\\owner/.test(WF)) {
  ok("el .exe owner se compila en Output\\owner (no pisa el de clientes)");
} else falla("el .exe owner se compilaria sobre el de clientes");
// El /O de ISCC se resuelve contra el directorio actual y el OutputDir del
// .iss contra la carpeta del script: con una ruta relativa el .exe termina en
// otro lado y el paso muere en el Move-Item, sin decir por que.
if (/\$salida = Join-Path \(Get-Location\)\.Path/.test(WF)) {
  ok("  la carpeta de salida del owner es una ruta absoluta");
} else falla("la salida del .exe owner es relativa: ISCC puede escribirla en otro lado");

// --- 6b-bis) el instalador owner NO puede salir en un repo publico ---
// owner-latest lleva un .exe PRE-ACTIVADO como Pro. El diseño asume un repo
// PRIVADO, donde ese Release solo lo ve el dueño. En un repo publico los
// Releases son URLs publicas: publicarlo es regalar el producto entero a
// cualquiera con el link, y encima en silencio (el build queda verde).
if (/name: Guardia de visibilidad del repositorio/.test(WF)) {
  ok("hay una guardia de visibilidad antes del bloque owner");
} else {
  falla("sin guardia de visibilidad: si el repo es publico, owner-latest " +
        "publicaria el instalador pre-activado al alcance de cualquiera");
}
if (/github\.event\.repository\.private/.test(WF)) {
  ok("  la guardia mira la visibilidad REAL del repositorio");
} else falla("la guardia no consulta github.event.repository.private");
{
  const iGuard = WF.indexOf("- name: Guardia de visibilidad del repositorio");
  const iLic = WF.indexOf("- name: Escribir licencia owner");
  if (iGuard >= 0 && iLic >= 0 && iGuard < iLic) {
    ok("  la guardia corre ANTES de pedir la licencia de dueño");
  } else falla("la guardia tiene que correr antes del primer paso owner");
  if (/steps\.owner_guard\.outputs\.publicar == 'si'/.test(WF)) {
    ok("  el bloque owner solo sigue si la guardia lo habilita");
  } else falla("el bloque owner no depende de la guardia: la puede saltear");
}

// --- 6c) el bloque owner NUNCA puede voltear el build ---
// Corre en CADA push a main y depende de un servidor EXTERNO (le pide la
// licencia del dueño). Sin esto, un 503 pasajero de ese servidor dejaba main
// en rojo aunque el instalador de clientes hubiera salido perfecto -- y el de
// clientes ya esta publicado a esa altura, asi que el rojo no protege nada.
const PASOS_OWNER = [
  "Escribir licencia owner",
  "Verificar que el build owner lleva la licencia adentro",
  "Compilar instalador owner",
  "Armar la version portable owner",
  "Publicar instalador owner como Release",
];
for (const nombre of PASOS_OWNER) {
  const i = WF.indexOf(`- name: ${nombre}`);
  if (i < 0) { falla(`falta el paso owner "${nombre}"`); continue; }
  const sig = WF.indexOf("\n      - name: ", i + 10);
  const bloque = WF.slice(i, sig < 0 ? WF.length : sig);
  if (/continue-on-error: true/.test(bloque)) ok(`  "${nombre}" no voltea el build`);
  else {
    falla(`el paso owner "${nombre}" puede voltear el build: un fallo del ` +
          `servidor de licencias dejaria main en rojo sin culpa del codigo`);
  }
}
if (/name: Resumen del build owner/.test(WF)) {
  ok("un build owner salteado queda a la vista en el resumen del run");
} else falla("sin paso de resumen, un owner salteado pasaria en silencio");

// Los pasos que pegan contra servicios externos (npm, python.org, PyPI,
// chocolatey) reintentan: un corte pasajero no puede poner el PR en rojo.
const reintentos = (WF.match(/Reintentar \{/g) || []).length;
if (reintentos >= 6) ok(`${reintentos} pasos de red reintentan antes de fallar`);
else falla(`solo ${reintentos} pasos reintentan: un 503 pasajero voltea el PR`);

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

// --- 8) el cliente NO recibe el panel legacy de Streamlit ---
// streamlit no se instala en el runtime del cliente (requirements-desktop.txt),
// asi que estos archivos eran peso muerto que ademas FALLABA si los tocaba.
// core\i18n.py es el peor: tiene "import streamlit as st" duro.
const pyLine = lineasFiles.find((l) => /\.\.\\\*\.py/.test(l));
const batLine = lineasFiles.find((l) => /\.\.\\\*\.bat/.test(l));
const coreLine = lineasFiles.find((l) => /\.\.\\core\\\*/.test(l));
const chequeos = [
  [pyLine, "dashboard_app.py", "el panel Streamlit viejo"],
  [pyLine, "styles.py", "el sistema de diseño de ese panel"],
  [batLine, "LEGACY_STREAMLIT.bat", "el lanzador de algo que no esta instalado"],
  [coreLine, "i18n.py", "tiene 'import streamlit' duro"],
];
for (const [linea, archivo, porque] of chequeos) {
  if (!linea) { falla(`no encontre la linea Source de ${archivo}`); continue; }
  const m = /Excludes:\s*"([^"]*)"/i.exec(linea);
  const excl = m ? m[1].split(",").map((x) => x.trim()) : [];
  if (excl.includes(archivo)) ok(`  ${archivo} NO se distribuye (${porque})`);
  else falla(`${archivo} se le entrega al cliente y ${porque}`);
}
if (lineasFiles.some((l) => /\.streamlit/.test(l))) {
  falla("[Files] todavia copia la carpeta .streamlit al cliente");
} else ok("  la carpeta .streamlit no se distribuye");

// --- 9) el puerto no puede chocar con otra app ---
// Electron pide el puerto 0: el sistema operativo devuelve uno LIBRE. Un puerto
// fijo chocaria con cualquier otra cosa que ya lo tenga tomado.
if (/listen\(0,/.test(MAIN)) {
  ok("Electron pide un puerto libre al sistema (listen(0)), no uno fijo");
} else falla("Electron usa un puerto fijo: chocaria con otra app que lo tenga abierto");
// y los lanzadores .bat lo resuelven con core/puerto.py, que hace bind real
const INICIAR = fs.readFileSync(path.join(RAIZ, "INICIAR.bat"), "utf8");
if (/buscar_puerto/.test(INICIAR)) ok("INICIAR.bat busca un puerto libre antes de arrancar");
else falla("INICIAR.bat no busca puerto libre: moriria si 8000 esta tomado");

// --- 10) el instalador OWNER es inalcanzable para un cliente ---
// Es el que arranca pre-activado como Pro: si un cliente pudiera bajarlo,
// tendria el producto completo gratis. Se publica en un Release aparte
// (owner-latest) que api/descarga.js NO conoce, y el repo es privado.
const DESCARGA = fs.readFileSync(path.join(RAIZ, "api/descarga.js"), "utf8");
if (/owner-latest|Owner_Setup/i.test(DESCARGA)) {
  falla("api/descarga.js menciona el release OWNER: un cliente podria bajarlo");
} else ok("api/descarga.js no conoce owner-latest (el cliente no puede pedirlo)");
// Los tags servibles tienen que ser constantes del propio archivo, no algo que
// el cliente pueda elegir por querystring.
const tags = [...DESCARGA.matchAll(/tag:\s*"([^"]+)"/g)].map((m) => m[1]);
if (!tags.length) falla("no encontre los tags de release en api/descarga.js");
else if (tags.some((t) => !["pc-latest", "android-latest"].includes(t))) {
  falla(`api/descarga.js puede servir tags inesperados: ${tags.join(", ")}`);
} else {
  const unicos = [...new Set(tags)];
  ok(`api/descarga.js solo sirve ${unicos.join(" y ")} (tags fijos, no elegibles)`);
}

// El build owner no puede publicar un instalador SIN la licencia adentro:
// el .iss la incluye con skipifsourcedoesntexist, o sea que compilaria igual.
if (/Verificar que el build owner lleva la licencia adentro/.test(WF)) {
  ok("el CI corta si el build owner no lleva owner_licencia.json adentro");
} else {
  falla("sin esa verificacion, un build owner podria publicar en owner-latest " +
        "un instalador NO pre-activado, con cara de owner");
}

// --- 11) la carpeta INSTALADOR/ del ZIP de GitHub ---
// El .exe pesa ~126 MB y GitHub rechaza archivos de mas de 100 MB, asi que la
// carpeta no lo lleva adentro: lleva dos lanzadores que lo traen del Release.
const DIR_INST = path.join(RAIZ, "INSTALADOR");
for (const archivo of ["LEEME.md", "INSTALAR_CLIENTE.bat", "INSTALAR_OWNER.bat"]) {
  if (fs.existsSync(path.join(DIR_INST, archivo))) ok(`  INSTALADOR/${archivo} existe`);
  else falla(`falta INSTALADOR/${archivo}`);
}
// Si alguien commitea el .exe igual, el push lo rechaza GitHub y el repo queda
// trabado. Mejor que lo diga el test antes que el remoto.
for (const suelto of fs.existsSync(DIR_INST) ? fs.readdirSync(DIR_INST) : []) {
  const bytes = fs.statSync(path.join(DIR_INST, suelto)).size;
  if (bytes > 100 * 1024 * 1024) {
    falla(`INSTALADOR/${suelto} pesa ${(bytes / 1048576).toFixed(0)} MB: GitHub ` +
          "rechaza el push arriba de 100 MB. Va al Release, no al repo.");
  }
}
// INSTALAR_OWNER.bat le da a quien lo abra la URL del Release owner (el
// instalador pre-activado). Si se colara en el instalador del CLIENTE, cada
// comprador se llevaria ese cartel indicador puesto. Los wildcards de raiz del
// .iss no son recursivos, asi que hoy no se cuela; esto lo fija.
const lineasRaiz = lineasFiles.filter((l) => /Source:\s*"\.\.\\\*\./i.test(l));
const raizRecursiva = lineasRaiz.filter((l) => /recursesubdirs/i.test(l));
if (raizRecursiva.length) {
  falla("un wildcard de la raiz del .iss usa recursesubdirs: se llevaria " +
        "INSTALADOR\\INSTALAR_OWNER.bat (y su URL del release owner) al cliente");
} else ok(`  los ${lineasRaiz.length} wildcards de raiz no son recursivos ` +
          "(INSTALADOR/ no se cuela al cliente)");
if (lineasFiles.some((l) => /INSTALADOR/i.test(l))) {
  falla("[Files] empaqueta la carpeta INSTALADOR: el cliente recibiria el " +
        "lanzador del build owner");
} else ok("  [Files] no empaqueta INSTALADOR/");

// El lanzador del cliente baja lo publico; el del owner NO lleva credenciales
// (la autorizacion es la sesion de GitHub en el navegador).
const BAT_CLI = fs.existsSync(path.join(DIR_INST, "INSTALAR_CLIENTE.bat"))
  ? fs.readFileSync(path.join(DIR_INST, "INSTALAR_CLIENTE.bat"), "utf8") : "";
const BAT_OWN = fs.existsSync(path.join(DIR_INST, "INSTALAR_OWNER.bat"))
  ? fs.readFileSync(path.join(DIR_INST, "INSTALAR_OWNER.bat"), "utf8") : "";
// La demo ABIERTA se dio de baja: /api/descarga?demo=1 devuelve 410 y ya no
// existe ninguna descarga publica que un .bat pueda usar sin pagar. Ahora el
// .bat pide el link propio del comprador. Dos cosas que no se pueden aflojar:
//   - que no quede una URL de descarga fija adentro (seria la demo abierta
//     otra vez, por la puerta de atras);
//   - que valide el link pegado contra dominios oficiales, porque si no este
//     .bat baja y EJECUTA el binario que sea que le peguen.
if (/set\s+"URL=https?:\/\//i.test(BAT_CLI)) {
  falla("INSTALAR_CLIENTE.bat deja una URL de descarga fija: reabre la demo abierta");
} else ok("  INSTALAR_CLIENTE.bat no lleva ninguna URL de descarga fija");
if (/findstr[^\n]*mvfbaia/i.test(BAT_CLI)) {
  ok("  INSTALAR_CLIENTE.bat valida que el link pegado sea de un dominio oficial");
} else {
  falla("INSTALAR_CLIENTE.bat no valida el link pegado: ejecutaria un binario " +
        "de cualquier origen");
}
if (/owner-latest|Owner_Setup/i.test(BAT_CLI)) {
  falla("INSTALAR_CLIENTE.bat menciona el release OWNER: un cliente lo veria");
} else ok("  INSTALAR_CLIENTE.bat no menciona el release owner");
if (/releases\/tag\/owner-latest/.test(BAT_OWN)) {
  ok("  INSTALAR_OWNER.bat manda al Release privado owner-latest");
} else falla("INSTALAR_OWNER.bat no apunta al Release owner-latest");
const BAT_CLI_ZIP = fs.existsSync(path.join(DIR_INST, "INSTALAR_CLIENTE_SIN_INSTALADOR.bat"))
  ? fs.readFileSync(path.join(DIR_INST, "INSTALAR_CLIENTE_SIN_INSTALADOR.bat"), "utf8") : "";
// Un token/clave hardcodeado en un .bat del repo es un secreto commiteado.
for (const [re, que] of [[/gh[pousr]_[A-Za-z0-9]{20,}/, "un token de GitHub"],
                         [/github_pat_[A-Za-z0-9_]{20,}/, "un PAT de GitHub"],
                         [/Authorization:|Bearer\s+\S/i, "una cabecera de autorizacion"]]) {
  if (re.test(BAT_OWN) || re.test(BAT_CLI) || re.test(BAT_CLI_ZIP)) {
    falla(`los .bat de INSTALADOR traen ${que} adentro`);
  }
}
ok("  ningun .bat de INSTALADOR lleva token ni clave hardcodeada");

// --- 12) la version portable (.zip, sin instalador) ---
// Para empresas que bloquean ejecutar .exe pero permiten .bat/.vbs: mismo
// motor, misma licencia, sin instalar nada.
if (BAT_CLI_ZIP) {
  if (/MV_FBA_IA_Portable\.zip/.test(BAT_CLI_ZIP)) {
    ok("  INSTALAR_CLIENTE_SIN_INSTALADOR.bat guarda el .zip portable, no el .exe");
  } else falla("INSTALAR_CLIENTE_SIN_INSTALADOR.bat ya no apunta al .zip portable");
  if (/set\s+"URL=https?:\/\//i.test(BAT_CLI_ZIP)) {
    falla("INSTALAR_CLIENTE_SIN_INSTALADOR.bat deja una URL fija: reabre la demo abierta");
  } else ok("  INSTALAR_CLIENTE_SIN_INSTALADOR.bat no lleva URL de descarga fija");
  if (/owner-latest|Owner_Setup|Portable_Owner/i.test(BAT_CLI_ZIP)) {
    falla("INSTALAR_CLIENTE_SIN_INSTALADOR.bat menciona el release OWNER: un cliente lo veria");
  } else ok("  INSTALAR_CLIENTE_SIN_INSTALADOR.bat no menciona el release owner");
} else falla("falta INSTALADOR/INSTALAR_CLIENTE_SIN_INSTALADOR.bat");

for (const archivo of ["crear_accesos.vbs", "CREAR_ACCESOS_DIRECTOS.bat", "DESINSTALAR.bat", "LEEME_PORTABLE.md"]) {
  if (fs.existsSync(path.join(RAIZ, "installer", "portable", archivo))) {
    ok(`  installer/portable/${archivo} existe`);
  } else falla(`falta installer/portable/${archivo}`);
}
// Nada en installer/ se cuela al cliente por wildcard (ver chequeo 11): los
// .iss solo listan archivos SUELTOS de su propia carpeta (Iniciar_Silencioso.vbs,
// assets\icon.ico), nunca "installer\*" ni "installer\portable\*". Si algun dia
// alguien agrega un wildcard asi, el paquete portable se filtraria dentro del
// instalador de Electron sin que nadie lo pidiera.
if (/Source:\s*"(\.\.\\)?installer\\(\*|portable\\\*)"/i.test(ISS)) {
  falla('el .iss tiene un wildcard sobre "installer\\*" o "installer\\portable\\*": ' +
        "se llevaria los lanzadores de la version portable al instalador .exe");
} else ok("  el .iss no tiene ningun wildcard sobre installer\\ (portable\\ no se cuela)");

// El workflow tiene que armar y publicar el .zip portable, para las dos
// versiones (cliente en pc-latest, owner en owner-latest) -- si alguien
// borra el paso sin querer, el boton "sin instalador" de la web quedaria
// pidiendo un asset que nunca se publica (502 descarga_no_disponible).
if (/MV_FBA_IA_Portable\.zip/.test(WF) && /MV_FBA_IA_Portable_Owner\.zip/.test(WF)) {
  ok("  el workflow arma y publica el .zip portable (cliente y owner)");
} else falla("el workflow no arma/publica MV_FBA_IA_Portable(.zip|_Owner.zip): " +
             "el boton 'sin instalador' de la web quedaria roto");
if (/Smoke test de la version portable/.test(WF)) {
  ok("  el CI arranca el .zip portable YA DESCOMPRIMIDO y prueba /health");
} else falla("no hay smoke test de la version portable: se podria publicar un " +
             ".zip que no arranca sin que el CI lo note");

// api/descarga.js: el .zip portable tiene que estar en el MISMO tag que el
// .exe (pc-latest) -- si tuviera un tag propio, el chequeo de arriba sobre
// "tags fijos, no elegibles" no lo cubriria y alguien podria colar un tag
// nuevo sin que ningun test lo note.
if (/RELEASE_PC_BAT\s*=\s*\{\s*tag:\s*"pc-latest"/.test(DESCARGA)) {
  ok("  api/descarga.js sirve el .zip portable bajo el mismo tag pc-latest");
} else falla("RELEASE_PC_BAT no esta atado al tag pc-latest en api/descarga.js");

// --- 13) la herramienta que pasa una instalacion a OWNER ---
// Convierte una instalacion normal en Pro sin recompilar. Tiene que cumplir
// DOS cosas: no viajar al cliente, y no servir de nada aunque igual llegara.
const ACT_BAT = fs.existsSync(path.join(DIR_INST, "ACTIVAR_OWNER.bat"))
  ? fs.readFileSync(path.join(DIR_INST, "ACTIVAR_OWNER.bat"), "utf8") : "";
const ACT_PY = fs.existsSync(path.join(DIR_INST, "activar_owner.py"))
  ? fs.readFileSync(path.join(DIR_INST, "activar_owner.py"), "utf8") : "";
if (ACT_BAT && ACT_PY) ok("  INSTALADOR/ACTIVAR_OWNER.bat + activar_owner.py existen");
else falla("falta ACTIVAR_OWNER.bat o activar_owner.py en INSTALADOR/");

// No se empaquetan: el chequeo 11 ya prueba que [Files] no toca INSTALADOR/ y
// que los wildcards de raiz no son recursivos. Aca se fija lo especifico.
for (const f of ["ACTIVAR_OWNER.bat", "activar_owner.py"]) {
  if (lineasFiles.some((l) => l.includes(f))) {
    falla(`[Files] empaqueta ${f}: el cliente recibiria la herramienta de owner`);
  }
}
ok("  el instalador no empaqueta la herramienta de activacion owner");

// La propiedad que la hace segura aunque se filtre: NO calcula la clave, se la
// PIDE al servidor, que exige prueba de acceso al repo. Si algun dia alguien
// "simplificara" esto calculando el HMAC localmente, haria falta meter
// LICENCIA_SECRETO en el archivo -- y ahi si, cualquiera que lo consiga se
// fabrica licencias Pro infinitas para cualquier email.
if (/api\/licencia\?dueno=1/.test(ACT_PY)) {
  ok("  activar_owner.py PIDE la clave al servidor (no la fabrica)");
} else falla("activar_owner.py no pide la clave a /api/licencia?dueno=1");
// Se mira el CODIGO, no la prosa: el docstring explica justamente por que no
// se usa HMAC ni LICENCIA_SECRETO, y nombrarlos ahi no es usarlos (mismo
// criterio que el chequeo de netstat en verificar_lanzadores.mjs).
const ACT_PY_CODIGO = ACT_PY
  .replace(/"""[\s\S]*?"""/g, "")   // docstrings
  .replace(/'''[\s\S]*?'''/g, "")
  .replace(/#.*$/gm, "");           // comentarios de linea
let calculaLocal = false;
for (const [re, que] of [[/\bhmac\b/i, "hmac"], [/hashlib/, "hashlib"],
                         [/LICENCIA_SECRETO/, "LICENCIA_SECRETO"]]) {
  if (re.test(ACT_PY_CODIGO)) {
    calculaLocal = true;
    falla(`activar_owner.py usa ${que}: estaria calculando la clave localmente, ` +
          "lo que obliga a llevar el secreto de firma adentro del archivo");
  }
}
if (!calculaLocal) ok("  activar_owner.py no calcula la clave localmente (no lleva el secreto)");

// Antes de escribir, valida el formato: si el servidor contesta cualquier otra
// cosa (una pagina de error, un JSON raro), un owner_licencia.json invalido
// haria fallar la activacion en silencio al abrir el programa.
if (/MVFBA\(-\[A-F0-9\]\{4\}\)\{4\}/.test(ACT_PY)) {
  ok("  activar_owner.py valida el formato de la clave antes de escribirla");
} else falla("activar_owner.py no valida el formato MVFBA-XXXX-XXXX-XXXX-XXXX");

// Ningun token hardcodeado en la herramienta (mismo criterio que los otros).
for (const [re, que] of [[/gh[pousr]_[A-Za-z0-9]{20,}/, "un token de GitHub"],
                         [/github_pat_[A-Za-z0-9_]{20,}/, "un PAT de GitHub"]]) {
  if (re.test(ACT_BAT) || re.test(ACT_PY)) {
    falla(`la herramienta de activacion owner trae ${que} adentro`);
  }
}
ok("  la herramienta de activacion owner no lleva ningun token adentro");

console.log("");
if (fallos.length) {
  console.error(`FALLO: ${fallos.length} problema(s) en el instalador.`);
  process.exit(1);
}
console.log("OK: el instalador no filtra documentacion interna, tiene metadatos, "
  + "deja elegir carpeta, abre la app de Electron, desinstala sin residuos y "
  + "separa owner de clientes.");
