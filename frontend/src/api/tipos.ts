// Tipos de los contratos de la API local (passthrough de las funciones
// Python — ver api_rutas.py). Solo los campos que la UI consume; el resto
// viaja igual y se ignora sin romper.

export interface EstadoLicencia {
  registrado: boolean;
  nombre?: string;
  email?: string;
  licencia: boolean;
  dias_restantes: number;
  vigente: boolean;
}

export interface Prefs {
  idioma: "es" | "en" | "pt";
  producto_activo_id: string;
  tema: string;
  modo_demo: string;
}

export interface Producto {
  id: number;
  nombre: string;
  asin: string;
  costo: number; flete: number; arancel_pct: number; prep: number;
  fba_fee: number;
  landed: number; precio: number; neto: number;
  margen: number; roi: number;
  semaforo: "verde" | "amarillo" | "rojo";
  techo_demanda: number;
  ventas_ingreso: number; ventas_neto: number;
  ventas_unidades: number; ventas_ordenes: number;
  capital_pipeline: number; sueldo_meseta_teorico: number;
  notas?: string;
}

export interface ResumenPortafolio {
  ok: boolean; n_productos: number;
  capital_pipeline_total?: number; sueldo_meseta_proyectado?: number;
  ingreso_real?: number; neto_real?: number; margen_promedio_pct?: number;
  semaforos?: { verde: number; amarillo: number; rojo: number };
  productos: Producto[];
  mensaje?: string;
}

export interface ResultadoPricing {
  precio: number; referral: number; fba_fee: number; ads: number;
  landed: number; neto: number; margen_pct: number; roi_pct: number;
  semaforo: "verde" | "amarillo" | "rojo";
  estrategia: string; precio_objetivo: number | null;
  break_even: number | null;
}

export interface RespuestaChat {
  texto: string;
  modo: "online" | "offline";
  proveedor?: string;
}

export interface MensajeChat {
  role: "user" | "assistant";
  content: string;
}

export interface SeccionTutorial {
  clave: string; titulo: string; para_que: string;
  pasos: string[]; tips: string[];
}

export interface EstadoAsistente {
  ok: boolean; modo: string; proveedor: string | null; mensaje: string;
}

export interface ConfigEstado {
  llm?: string; keepa?: string; email?: string; marketplace?: string;
  claves: Record<string, string>;
  ia_provider: string;
  acos_pct: number; umbral_verde: number; umbral_amarillo: number;
  [k: string]: unknown;
}

export interface Alerta {
  fecha: string; asunto: string; para: string; enviado: number;
}

export interface Oportunidad {
  nicho: string; seed_origen: string; interes_proxy: number;
  potencial: number; veredicto: string; comentario: string;
  n_competidores: number | null; ventas_estim_total: number | null;
  precio_mediana: number | null; fuente_precio: string;
}

export interface KeywordMotor {
  keyword: string; interes: number; mejor_rank: number; apariciones: number;
}

export interface ProductoEstrella {
  asin: string; titulo: string; precio: number | null; bsr: number | null;
  ventas_estim: number; rating: number | null; resenas: number;
  link: string; link_resenas: string;
}

export interface FilaProyeccion {
  mes: number; vendidas: number; cobrado: number;
  sueldo: number; caja: number; capital_atado: number;
  [k: string]: number;
}
