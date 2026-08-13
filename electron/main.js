// © 2026 Martín Viera. Todos los derechos reservados.
// main.js — MV FBA IA como aplicacion de escritorio con Electron.
//
// POR QUE ELECTRON Y NO pywebview
// -------------------------------
// pywebview dibujaba la ventana con el runtime WebView2 de Microsoft Edge, que
// es un componente del SISTEMA: si la maquina no lo tenia, la app no podia
// abrir su ventana y caia a mostrarse en el navegador -- el cliente veia "una
// web" en vez de un programa. Electron trae su propio Chromium adentro, asi
// que no depende de nada instalado en la maquina: abre siempre igual.
//
// QUE HACE
// --------
// 1. Busca un puerto libre.
// 2. Levanta el motor Python (uvicorn app:app) con el runtime embebido.
// 3. Espera a que /health responda.
// 4. Abre la ventana nativa apuntando a ese localhost.
// 5. Al cerrar la ventana, apaga el motor. Nunca deja el proceso huerfano.
const { app, BrowserWindow, dialog, shell } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const net = require("net");
const http = require("http");

const TITULO = "MV FBA IA";
let ventana = null;
let motor = null;      // proceso de uvicorn
let apagando = false;

// --------------------------------------------------------------------------
// Rutas
// --------------------------------------------------------------------------
// Empaquetado, el .exe queda en {app}\desktop\MV FBA IA.exe, y el programa
// Python (app.py, agents\, runtime\) vive un nivel mas arriba, en {app}.
// En desarrollo se corre desde electron\, asi que la raiz es el padre.
function raizPrograma() {
  if (app.isPackaged) return path.dirname(path.dirname(process.execPath));
  return path.join(__dirname, "..");
}

// Mismo orden de preferencia que _entorno.bat: primero el runtime embebido que
// trae el instalador (tiene las dependencias ya instaladas), y solo si no esta
// se prueba un Python del sistema (caso "clone del repositorio").
function buscarPython(raiz) {
  const candidatos = [
    path.join(raiz, "runtime", "pythonw.exe"),
    path.join(raiz, "runtime", "python.exe"),
  ];
  for (const c of candidatos) if (fs.existsSync(c)) return c;
  return process.platform === "win32" ? "pythonw.exe" : "python3";
}

function puertoLibre() {
  return new Promise((resolve, reject) => {
    const s = net.createServer();
    s.on("error", reject);
    s.listen(0, "127.0.0.1", () => {
      const p = s.address().port;
      s.close(() => resolve(p));
    });
  });
}

function salud(puerto) {
  return new Promise((resolve) => {
    const req = http.get(
      { host: "127.0.0.1", port: puerto, path: "/health", timeout: 2000 },
      (res) => { res.resume(); resolve(res.statusCode === 200); });
    req.on("error", () => resolve(false));
    req.on("timeout", () => { req.destroy(); resolve(false); });
  });
}

async function esperarMotor(puerto, segundos = 90) {
  const fin = Date.now() + segundos * 1000;
  while (Date.now() < fin) {
    if (motor && motor.exitCode !== null) return false;   // murio al arrancar
    if (await salud(puerto)) return true;
    await new Promise((r) => setTimeout(r, 400));
  }
  return false;
}

// --------------------------------------------------------------------------
// Motor Python
// --------------------------------------------------------------------------
function arrancarMotor(raiz, puerto) {
  const python = buscarPython(raiz);
  const args = ["-m", "uvicorn", "app:app", "--host", "127.0.0.1",
                "--port", String(puerto), "--log-level", "warning"];
  const p = spawn(python, args, {
    cwd: raiz,
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1" },
  });
  let err = "";
  // Se guarda el stderr para poder MOSTRARLO si el motor no levanta. Antes el
  // lanzador corria oculto con pythonw y el error no lo veia nadie.
  if (p.stderr) p.stderr.on("data", (d) => { err += d.toString(); if (err.length > 8000) err = err.slice(-8000); });
  if (p.stdout) p.stdout.on("data", () => {});
  p.on("error", (e) => { err += "\n" + e.message; });
  p.ultimoError = () => err;
  return p;
}

function apagarMotor() {
  if (!motor || apagando) return;
  apagando = true;
  try {
    if (process.platform === "win32" && motor.pid) {
      // /T tambien mata a los hijos: uvicorn con reload o workers deja arbol.
      spawn("taskkill", ["/pid", String(motor.pid), "/T", "/F"],
            { windowsHide: true, stdio: "ignore" });
    } else {
      motor.kill();
    }
  } catch (_) { /* ya estaba muerto */ }
  motor = null;
}

// --------------------------------------------------------------------------
// Ventana
// --------------------------------------------------------------------------
function iconoVentana(raiz) {
  for (const rel of [["desktop", "icon.ico"], ["assets", "icon.ico"],
                     ["frontend", "dist", "icon.png"]]) {
    const p = path.join(raiz, ...rel);
    if (fs.existsSync(p)) return p;
  }
  return undefined;
}

function crearVentana(raiz, url) {
  ventana = new BrowserWindow({
    title: TITULO,
    width: 1360,
    height: 880,
    minWidth: 1024,
    minHeight: 680,
    show: false,                     // se muestra recien cuando termino de pintar
    autoHideMenuBar: true,           // sin la barra File/Edit/View de Electron
    icon: iconoVentana(raiz),
    backgroundColor: "#1e3a8a",      // navy del sistema de diseño, sin flash blanco
    webPreferences: {
      // El panel es una SPA propia servida desde 127.0.0.1: no necesita ni
      // Node ni acceso al sistema desde el render.
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  });
  ventana.once("ready-to-show", () => { ventana.show(); ventana.focus(); });
  ventana.on("closed", () => { ventana = null; });

  // Un link externo (proveedores, Amazon, soporte) abre en el navegador del
  // sistema, no adentro de la app: si no, el usuario queda atrapado en una
  // ventana sin barra de direcciones ni boton de volver.
  ventana.webContents.setWindowOpenHandler(({ url: destino }) => {
    if (/^https?:/i.test(destino)) shell.openExternal(destino);
    return { action: "deny" };
  });
  ventana.webContents.on("will-navigate", (ev, destino) => {
    if (!destino.startsWith(url)) { ev.preventDefault(); shell.openExternal(destino); }
  });

  ventana.loadURL(url);
}

function morirCon(titulo, mensaje) {
  dialog.showErrorBox(titulo, mensaje);
  apagarMotor();
  app.exit(1);
}

// --------------------------------------------------------------------------
// Arranque
// --------------------------------------------------------------------------
// Sin esto, abrir el acceso directo dos veces levanta DOS motores Python
// peleando por la base de datos.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (ventana) { if (ventana.isMinimized()) ventana.restore(); ventana.focus(); }
  });

  app.whenReady().then(async () => {
    const raiz = raizPrograma();
    if (!fs.existsSync(path.join(raiz, "app.py"))) {
      morirCon(TITULO, "No encuentro los archivos del programa en:\n" + raiz +
        "\n\nSi instalaste MV FBA IA, reinstalalo: la carpeta quedo incompleta.");
      return;
    }
    let puerto;
    try {
      puerto = await puertoLibre();
    } catch (e) {
      morirCon(TITULO, "No se pudo reservar un puerto local.\n\n" + e.message);
      return;
    }
    motor = arrancarMotor(raiz, puerto);
    const ok = await esperarMotor(puerto);
    if (!ok) {
      const detalle = (motor && motor.ultimoError && motor.ultimoError()) || "(sin detalle)";
      morirCon(TITULO,
        "El motor de MV FBA IA no arranco.\n\n" +
        "Detalle tecnico:\n" + detalle.slice(-1500));
      return;
    }
    crearVentana(raiz, `http://127.0.0.1:${puerto}/`);
  });

  // El motor se apaga SIEMPRE: al cerrar la ventana, al salir, y si el proceso
  // se muere de cualquier otra forma. Un uvicorn huerfano dejaria el puerto
  // tomado y la base abierta.
  app.on("window-all-closed", () => { apagarMotor(); app.quit(); });
  app.on("before-quit", apagarMotor);
  process.on("exit", apagarMotor);
  process.on("SIGINT", () => { apagarMotor(); process.exit(0); });
  process.on("SIGTERM", () => { apagarMotor(); process.exit(0); });
}
