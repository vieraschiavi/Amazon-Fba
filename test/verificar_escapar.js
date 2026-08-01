/* verificar_escapar.js — Test de regresion de escapar() (mobile/js/seguro.js).
 *
 * escapar() es el unico punto por el que pasa un titulo de Amazon (Keepa/
 * Jungle Scout), un nombre de producto del usuario o cualquier otro dato
 * dinamico antes de insertarse en el DOM via innerHTML — incluida posicion de
 * ATRIBUTO (ej. value="${escapar(d.nombre)}" en el modal de producto). El bug
 * real que motiva este test: un titulo tan comun como 'Bamboo Set 10" Kitchen'
 * rompia el atributo porque escapar() no cubria comillas (arreglado en el
 * PR #53). Este test evita que alguien vuelva a sacar el escape de comillas
 * "para simplificar" sin darse cuenta de por que estan.
 *
 * Uso:   node test/verificar_escapar.js      (sale 0 si todo pasa, 1 si no)
 */
const { escapar } = require("../mobile/js/seguro.js");

const casos = [
  // [nombre, entrada, lo que NUNCA debe aparecer crudo en el resultado]
  ["titulo real de Amazon con pulgadas", 'Bamboo Utensil Set 10" Kitchen', ['10" Kitchen']],
  ["inyeccion por atributo (comilla doble)", '" autofocus onfocus="alert(1)', ['"']],
  ["inyeccion por atributo (comilla simple)", "' onmouseover='alert(1)", ["'"]],
  ["tag clasico", '<img src=x onerror=alert(1)>', ['<img', '>']],
  ["null", null, []],
  ["undefined", undefined, []],
  ["numero", 42, []],
];

let fallas = 0;

// 1) ningun caracter peligroso crudo sobrevive
for (const [nombre, entrada, prohibidos] of casos) {
  const salida = escapar(entrada);
  for (const p of prohibidos) {
    if (salida.includes(p)) {
      console.error(`FALLA  ${nombre}: "${p}" crudo en la salida -> ${salida}`);
      fallas++;
    }
  }
}

// 2) los 5 caracteres se escapan a su entidad exacta
const mapa = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
for (const [char, entidad] of Object.entries(mapa)) {
  const salida = escapar(char);
  if (salida !== entidad) {
    console.error(`FALLA  escapar("${char}") = "${salida}", esperaba "${entidad}"`);
    fallas++;
  }
}

// 3) simulacro real: renderizado dentro de un atributo value="...", como en
//    el modal de producto (abrirProducto() en mobile/js/app.js)
for (const [nombre, entrada] of casos) {
  if (typeof entrada !== "string") continue;
  const render = `<input value="${escapar(entrada)}">`;
  const cuerpo = render.slice('<input value="'.length, -2);
  if (/["'<>]/.test(cuerpo)) {
    console.error(`FALLA  ${nombre}: el atributo queda inyectable -> ${render}`);
    fallas++;
  }
}

if (fallas) {
  console.error(`\n${fallas} falla(s) en escapar().`);
  process.exit(1);
} else {
  console.log(`OK: escapar() cubre & < > " ' en los ${casos.length} casos + posicion de atributo.`);
  process.exit(0);
}
