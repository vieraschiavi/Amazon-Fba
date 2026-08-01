/* verificar_creditosia.mjs — Test de regresion de api/_creditosia.js contra
 * un servidor KV real (mock_kv_servidor.mjs emula la API REST de Upstash).
 *
 * Este modulo mueve plata real (saldo de creditos de IA, comprado con
 * MercadoPago/PayPal) y tenia 0% de cobertura de test: ni un solo caso de
 * borde de dinero estaba probado. Cubre especificamente los que la auditoria
 * senalo como faltantes: saldo insuficiente y recarga duplicada/doble-submit
 * (el resto -- clave de licencia invalida, demo vencida -- vive en
 * core/licencia.py y api/_licencia.js, modulos distintos).
 *
 * Uso:   node test/verificar_creditosia.mjs
 */
process.env.KV_REST_API_URL = "PLACEHOLDER";
process.env.KV_REST_API_TOKEN = "test-token";

import { iniciarMockKv } from "./mock_kv_servidor.mjs";

const kv = await iniciarMockKv();
process.env.KV_REST_API_URL = kv.url;

const {
  otorgarBonoBienvenidaSiNuevo, revisarSaldo, descontarCreditos,
  acreditarRecargaSiNueva, esPackRecarga, BONO_BIENVENIDA, PACKS_RECARGA,
} = await import("../api/_creditosia.js");

let fallas = 0;
function assert(cond, msg) {
  if (!cond) { console.error("FALLA  " + msg); fallas++; }
  else console.log("OK     " + msg);
}

// --- esPackRecarga: solo reconoce los packs reales ---
assert(esPackRecarga("creditos_9") === true, "esPackRecarga reconoce un pack real");
assert(esPackRecarga("plan_inventado") === false, "esPackRecarga rechaza un plan que no existe");
assert(esPackRecarga(undefined) === false, "esPackRecarga no rompe con undefined");

// --- otorgarBonoBienvenidaSiNuevo: idempotente (no regala el bono 2 veces) ---
{
  const email = "nueva@ejemplo.com";
  const primero = await otorgarBonoBienvenidaSiNuevo(email);
  const segundo = await otorgarBonoBienvenidaSiNuevo(email);
  assert(primero && primero.saldo === BONO_BIENVENIDA, "cuenta nueva recibe el bono de bienvenida completo");
  assert(segundo === null, "la MISMA cuenta no recibe el bono una segunda vez (no hay null-check roto)");
}

// --- revisarSaldo: sin cuenta / activo / saldo agotado ---
{
  const sinCuenta = await revisarSaldo("nunca-registrada@ejemplo.com", false);
  assert(sinCuenta.activo === false && sinCuenta.motivo === "sin_cuenta",
    "email sin registro de creditos: inactivo, motivo sin_cuenta");

  const email = "con-saldo@ejemplo.com";
  await otorgarBonoBienvenidaSiNuevo(email);
  const conSaldo = await revisarSaldo(email, false);
  assert(conSaldo.activo === true && conSaldo.saldo === BONO_BIENVENIDA,
    "cuenta con bono recien otorgado: activa, con el saldo completo");

  // CASO DE BORDE explicito pedido: saldo insuficiente (agotado a 0)
  await descontarCreditos(email, BONO_BIENVENIDA * 1000); // tokens de sobra para dejarlo en 0
  const agotado = await revisarSaldo(email, false);
  assert(agotado.activo === false && agotado.motivo === "saldo_agotado",
    "CASO DE BORDE: saldo en 0 -> inactivo, motivo saldo_agotado (no deja seguir gratis)");
}

// --- revisarSaldo con conLicenciaValidada: otorga el bono al vuelo ---
{
  const email = "licencia-vieja@ejemplo.com"; // compro antes de que existiera el sistema de creditos
  const r = await revisarSaldo(email, true);
  assert(r.activo === true && r.saldo === BONO_BIENVENIDA,
    "licencia validada por HMAC sin registro de creditos recibe el bono al vuelo (no queda afuera)");
}

// --- descontarCreditos: nunca queda negativo, acumula historico y semana ---
{
  const email = "consumo@ejemplo.com";
  await otorgarBonoBienvenidaSiNuevo(email);
  const despues1 = await descontarCreditos(email, 1000); // 1000 tokens = 1 credito (TOKENS_POR_CREDITO=1000)
  assert(despues1.saldo === BONO_BIENVENIDA - 1, "descontarCreditos resta tokens/1000 creditos del saldo");
  assert(despues1.n_preguntas === 1 && despues1.semana_preguntas === 1,
    "descontarCreditos acumula el contador de preguntas (total y de la semana)");

  // CASO DE BORDE explicito pedido: consumo que excede el saldo restante
  const despues2 = await descontarCreditos(email, (BONO_BIENVENIDA + 500) * 1000);
  assert(despues2.saldo === 0, "CASO DE BORDE: un consumo mayor al saldo nunca deja el saldo en negativo (clamp a 0)");
}

// --- acreditarRecargaSiNueva: el caso de borde central, doble-submit ---
{
  // Cuenta NUEVA: acreditarRecargaSiNueva tambien otorga el bono de
  // bienvenida "por las dudas" (cubre a quien compra un pack de creditos
  // sin haber tenido licencia antes) -- por eso el primer saldo es
  // bono + pack, no solo el pack. Documentado en el propio archivo.
  const email = "recarga@ejemplo.com";
  const idPago = "MP-12345";
  const esperadoPrimera = BONO_BIENVENIDA + PACKS_RECARGA.creditos_9.creditos;
  const primera = await acreditarRecargaSiNueva(email, idPago, "creditos_9");
  assert(primera && primera.saldo === esperadoPrimera,
    "la primera recarga de una cuenta nueva acredita bono de bienvenida + creditos del pack");

  // CASO DE BORDE explicito pedido: recarga duplicada / doble-submit
  const segunda = await acreditarRecargaSiNueva(email, idPago, "creditos_9");
  assert(segunda === null,
    "CASO DE BORDE: el MISMO payment_id (gracias.html recargada dos veces) no acredita el pack una segunda vez");

  const saldoFinal = await revisarSaldo(email, false);
  assert(saldoFinal.saldo === esperadoPrimera,
    "el saldo final tiene UN solo pack acreditado, no dos, tras el intento de doble-submit");

  // plan inexistente: no acredita nada
  const invalido = await acreditarRecargaSiNueva(email, "MP-otro-pago", "plan_inventado");
  assert(invalido === null, "un plan que no es un pack de recarga real no acredita nada");
}

// --- una segunda recarga con OTRO payment_id SI se acumula (no es doble-submit) ---
{
  const email = "recarga2@ejemplo.com";
  // primera recarga: cuenta nueva -> bono + pack chico
  const primera = await acreditarRecargaSiNueva(email, "MP-aaa", "creditos_9");
  const esperadoPrimera = BONO_BIENVENIDA + PACKS_RECARGA.creditos_9.creditos;
  assert(primera.saldo === esperadoPrimera,
    "primera recarga de esta cuenta: bono + pack chico (misma regla de arriba)");
  // segunda recarga: la cuenta YA existe -> el bono no se otorga de nuevo,
  // solo se suma el pack nuevo.
  const conDosPacks = await acreditarRecargaSiNueva(email, "MP-bbb", "creditos_19");
  const esperadoFinal = esperadoPrimera + PACKS_RECARGA.creditos_19.creditos;
  assert(conDosPacks.saldo === esperadoFinal,
    "segunda recarga con payment_id DISTINTO en cuenta YA existente: se acumula, sin bono duplicado");
}

await kv.cerrar();

if (fallas) {
  console.error(`\n${fallas} falla(s) en _creditosia.js.`);
  process.exit(1);
} else {
  console.log(`\nOK: _creditosia.js cubre bono idempotente, saldo agotado, descuento sin negativos y recarga doble-submit.`);
  process.exit(0);
}
