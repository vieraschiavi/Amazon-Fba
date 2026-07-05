// licencia.js — Registro y demo de 3 dias por usuario (PWA / Android / iOS).
//
// Nombre comercial: "MV Amazon FBA IA" (no cambia). Dominio/identificador
// interno de la licencia: "MV-Amazon-Fba".
//
// Sin servidor de cuentas: el registro y el reloj de 3 dias viven en el
// localStorage del telefono (misma logica que core/licencia.py para el
// programa de PC). Reinstalar la app y registrarse con otro email reinicia
// la demo -- limitacion conocida y aceptada de un esquema sin servidor.
// La licencia definitiva (post-pago) se valida offline con una firma HMAC
// derivada del email -- la misma formula que en el lado de PC, asi una
// clave emitida sirve en cualquiera de las dos puntas.
const Licencia = (() => {
  const DOMINIO = "MV-Amazon-Fba";
  const DIAS_DEMO = 3;
  const SECRETO = "mv-amazon-fba-2026-clave-de-firma";
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

  async function _hmacSha256Hex(secreto, mensaje) {
    const enc = new TextEncoder();
    const key = await crypto.subtle.importKey(
      "raw", enc.encode(secreto), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
    const firma = await crypto.subtle.sign("HMAC", key, enc.encode(mensaje));
    return Array.from(new Uint8Array(firma)).map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  async function generarClave(email) {
    const base = (email || "").trim().toLowerCase();
    const hex = (await _hmacSha256Hex(SECRETO, base + DOMINIO)).toUpperCase().slice(0, 16);
    const grupos = [hex.slice(0, 4), hex.slice(4, 8), hex.slice(8, 12), hex.slice(12, 16)].join("-");
    return `MVFBA-${grupos}`;
  }

  async function validarClave(email, clave) {
    const esperada = await generarClave(email);
    return (clave || "").trim().toUpperCase() === esperada;
  }

  async function activarLicencia(email, clave) {
    const ok = await validarClave(email, clave);
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
      titulo: "Bienvenido a MV Amazon FBA IA",
      sub: "Registrate para arrancar tu demo completa y gratis de 3 días — sin límites de funciones.",
      nombre: "Tu nombre", email: "Tu email",
      empezar: "Empezar mi demo de 3 días",
      falta_email: "Ingresá un email válido para arrancar la demo.",
      vencida_titulo: "Tu demo de 3 días venció",
      vencida_sub: "Activá tu licencia para seguir usando MV Amazon FBA IA sin límites, o escribinos para comprarla.",
      clave: "Clave de licencia", activar: "Activar licencia",
      clave_invalida: "Esa clave no es válida para este email.",
      clave_ok: "Licencia activada. ¡Gracias por tu compra!",
      contactar: "✉️ Escribinos para comprar tu licencia",
      badge_licencia: "Licencia activa",
      badge_demo: "Demo: {n} día(s) restante(s)",
    },
    en: {
      titulo: "Welcome to MV Amazon FBA IA",
      sub: "Register to start your full, free 3-day demo — no feature limits.",
      nombre: "Your name", email: "Your email",
      empezar: "Start my 3-day demo",
      falta_email: "Enter a valid email to start the demo.",
      vencida_titulo: "Your 3-day demo expired",
      vencida_sub: "Activate your license to keep using MV Amazon FBA IA with no limits, or contact us to buy it.",
      clave: "License key", activar: "Activate license",
      clave_invalida: "That key is not valid for this email.",
      clave_ok: "License activated. Thanks for your purchase!",
      contactar: "✉️ Contact us to buy your license",
      badge_licencia: "Active license",
      badge_demo: "Demo: {n} day(s) left",
    },
    pt: {
      titulo: "Bem-vindo ao MV Amazon FBA IA",
      sub: "Cadastre-se para começar seu demo completo e gratuito de 3 dias — sem limites de funções.",
      nombre: "Seu nome", email: "Seu email",
      empezar: "Começar meu demo de 3 dias",
      falta_email: "Digite um email válido para começar o demo.",
      vencida_titulo: "Seu demo de 3 dias venceu",
      vencida_sub: "Ative sua licença para continuar usando o MV Amazon FBA IA sem limites, ou fale conosco para comprá-la.",
      clave: "Chave de licença", activar: "Ativar licença",
      clave_invalida: "Essa chave não é válida para este email.",
      clave_ok: "Licença ativada. Obrigado pela compra!",
      contactar: "✉️ Fale conosco para comprar sua licença",
      badge_licencia: "Licença ativa",
      badge_demo: "Demo: {n} dia(s) restante(s)",
    },
  };

  return {
    DOMINIO, DIAS_DEMO, TXT,
    obtenerRegistro, registrar, diasRestantes,
    generarClave, validarClave, activarLicencia,
    tieneLicencia, demoVigente, estado,
  };
})();
