// © 2026 Martín Viera. Todos los derechos reservados.
// licencia.js — Registro y demo de 7 dias por usuario (PWA / Android / iOS).
//
// Nombre comercial: "MV FBA IA" (antes "MV Amazon FBA IA"; se saco "Amazon"
// del nombre para reducir riesgo de marca). El dominio/identificador interno
// de la licencia se deja SIN TOCAR a proposito: "MV-Amazon-Fba" — invisible
// para el usuario, y cambiar la formula HMAC invalidaria licencias ya
// emitidas a clientes que ya pagaron.
//
// Sin servidor de cuentas: el registro y el reloj de 7 dias viven en el
// localStorage del telefono (misma logica que core/licencia.py para el
// programa de PC). Reinstalar la app y registrarse con otro email reinicia
// la demo -- limitacion conocida y aceptada de un esquema sin servidor.
// La licencia definitiva (post-pago) se valida CONTRA EL SERVIDOR (api/validar):
// el secreto de firma vive solo en Vercel, nunca en el cliente, asi no se puede
// crackear leyendo el codigo. Activar pide internet una vez; despues anda offline.
const Licencia = (() => {
  const DOMINIO = "MV-Amazon-Fba";
  const DIAS_DEMO = 7;
  // El secreto de la licencia NO vive en el cliente (así no se puede crackear
  // por código): la validación se hace contra el servidor. La activación pide
  // internet una sola vez; después la licencia queda guardada y anda offline.
  const API_BASE = "https://amazon-fba-seven.vercel.app";
  const LS_REGISTRO = "mvfba_registro_v1";

  function _leer() {
    try {
      const raw = localStorage.getItem(LS_REGISTRO);
      return raw ? JSON.parse(raw) : null;
    } catch (_) { return null; }
  }
  function _guardar(reg) { localStorage.setItem(LS_REGISTRO, JSON.stringify(reg)); }

  function obtenerRegistro() { return _leer(); }

  function registrar(nombre, email) {
    const ya = _leer();
    if (ya) return ya;
    const reg = {
      nombre: (nombre || "").trim(), email: (email || "").trim(),
      dominio: DOMINIO, fechaRegistro: new Date().toISOString(),
      claveLicencia: null, fechaActivacion: null,
    };
    _guardar(reg);
    // Copia lateral best-effort en el servidor (api/demo-registro.js), SOLO
    // para poder mandar el recordatorio de "tu demo vence mañana" -- el
    // reloj real de los 7 dias sigue siendo el localStorage de arriba. Si
    // esto falla (sin internet en este instante, etc.) la demo funciona
    // exactamente igual: nunca se espera esta respuesta.
    try {
      fetch(API_BASE + "/api/demo-registro", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre: reg.nombre, email: reg.email }),
      }).catch(() => {});
    } catch (e) { /* sin fetch disponible o similar: no bloquea la demo */ }
    return reg;
  }

  function diasRestantes(reg) {
    reg = reg !== undefined ? reg : _leer();
    if (!reg || !reg.fechaRegistro) return 0;
    const inicio = new Date(reg.fechaRegistro).getTime();
    if (Number.isNaN(inicio)) return 0;
    const transcurridoDias = (Date.now() - inicio) / 86400000;
    return Math.max(0, DIAS_DEMO - transcurridoDias);
  }

  // Valida la licencia contra el servidor (el secreto vive solo ahí). Devuelve
  // true/false. Si no hay internet, lanza para que la UI avise "activá con
  // conexión" en vez de rechazar una clave legítima.
  async function validarClave(email, clave) {
    const resp = await fetch(API_BASE + "/api/validar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: (email || "").trim(), clave: (clave || "").trim() }),
    });
    if (!resp.ok) throw new Error("sin_conexion");
    const d = await resp.json();
    return Boolean(d && d.valido);
  }

  async function activarLicencia(email, clave) {
    let ok;
    try {
      ok = await validarClave(email, clave);
    } catch (e) {
      return { ok: false, mensaje: "sin_conexion" };  // activar requiere internet una vez
    }
    if (!ok) return { ok: false, mensaje: "clave_invalida" };
    let reg = _leer() || registrar("", email);
    reg = { ...reg, email: (email || "").trim(), claveLicencia: clave.trim().toUpperCase(),
             fechaActivacion: new Date().toISOString() };
    _guardar(reg);
    return { ok: true, mensaje: "clave_ok" };
  }

  function tieneLicencia(reg) {
    reg = reg !== undefined ? reg : _leer();
    return Boolean(reg && reg.claveLicencia);
  }

  function demoVigente(reg) {
    reg = reg !== undefined ? reg : _leer();
    return tieneLicencia(reg) || diasRestantes(reg) > 0;
  }

  function estado() {
    const reg = _leer();
    const restantes = diasRestantes(reg);
    return {
      registrado: Boolean(reg),
      licencia: tieneLicencia(reg),
      vigente: demoVigente(reg),
      diasRestantes: reg ? Math.ceil(restantes) : 0,
      nombre: (reg && reg.nombre) || "",
      email: (reg && reg.email) || "",
      dominio: DOMINIO,
    };
  }

  const TXT = {
    es: {
      titulo: "Bienvenido a MV FBA IA",
      sub: "Registrate para arrancar tu demo completa y gratis de 7 días — sin límites de funciones.",
      nombre: "Tu nombre", email: "Tu email",
      empezar: "Empezar mi demo de 7 días",
      falta_email: "Ingresá un email válido para arrancar la demo.",
      vencida_titulo: "Tu demo de 7 días venció",
      vencida_sub: "Activá tu licencia para seguir usando MV FBA IA sin límites, o escribinos para comprarla.",
      clave: "Clave de licencia", activar: "Activar licencia",
      clave_invalida: "Esa clave no es válida para este email.",
      sin_conexion: "Necesitás internet para activar la licencia la primera vez.",
      clave_ok: "Licencia activada. ¡Gracias por tu compra!",
      contactar: "Escribinos para comprar tu licencia",
      badge_licencia: "Licencia activa",
      badge_demo: "Demo: {n} día(s) restante(s)",
    },
    en: {
      titulo: "Welcome to MV FBA IA",
      sub: "Register to start your full, free 7-day demo — no feature limits.",
      nombre: "Your name", email: "Your email",
      empezar: "Start my 7-day demo",
      falta_email: "Enter a valid email to start the demo.",
      vencida_titulo: "Your 7-day demo expired",
      vencida_sub: "Activate your license to keep using MV FBA IA with no limits, or contact us to buy it.",
      clave: "License key", activar: "Activate license",
      clave_invalida: "That key is not valid for this email.",
      sin_conexion: "You need internet to activate the license the first time.",
      clave_ok: "License activated. Thanks for your purchase!",
      contactar: "Contact us to buy your license",
      badge_licencia: "Active license",
      badge_demo: "Demo: {n} day(s) left",
    },
    pt: {
      titulo: "Bem-vindo ao MV FBA IA",
      sub: "Cadastre-se para começar seu demo completo e gratuito de 7 dias — sem limites de funções.",
      nombre: "Seu nome", email: "Seu email",
      empezar: "Começar meu demo de 7 dias",
      falta_email: "Digite um email válido para começar o demo.",
      vencida_titulo: "Seu demo de 7 dias venceu",
      vencida_sub: "Ative sua licença para continuar usando o MV FBA IA sem limites, ou fale conosco para comprá-la.",
      clave: "Chave de licença", activar: "Ativar licença",
      clave_invalida: "Essa chave não é válida para este email.",
      sin_conexion: "Você precisa de internet para ativar a licença na primeira vez.",
      clave_ok: "Licença ativada. Obrigado pela compra!",
      contactar: "Fale conosco para comprar sua licença",
      badge_licencia: "Licença ativa",
      badge_demo: "Demo: {n} dia(s) restante(s)",
    },
  };

  return {
    DOMINIO, DIAS_DEMO, TXT,
    obtenerRegistro, registrar, diasRestantes,
    validarClave, activarLicencia,
    tieneLicencia, demoVigente, estado,
  };
})();
