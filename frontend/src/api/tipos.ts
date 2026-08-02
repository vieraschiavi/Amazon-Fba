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
  // Estimacion de ventas de mercado (cuanto vende el ASIN en Amazon). Sale de
  // Jungle Scout, de Keepa, o -- GRATIS, sin API -- del BSR publico de la
  // pagina de Amazon. null si aun no se estimo.
  ventas_estim_mes?: number | null;
  ventas_estim_fuente?: string | null;
  ventas_estim_fecha?: string | null;
  ventas_estim_confianza?: string | null;
  bsr?: number | null;
  bsr_categoria?: string | null;
  notas?: string;
}

export interface EstimacionVentas {
  ok: boolean;
  mensaje: string;
  ventas_estim_mes?: number;
  ventas_estim_fuente?: string;
  ventas_estim_fecha?: string;
  ventas_estim_confianza?: string;
  bsr?: number | null;
}

// Vendedores principales estimados desde el BSR publico (sin API paga) o desde
// un export de productos (Helium 10 / Jungle Scout) si el usuario ya lo paga.
export interface VendedorPrincipal {
  asin: string | null;
  titulo: string;
  precio: number | null;
  bsr: number | null;
  categoria: string | null;
  ventas_estim: number | null;
  confianza: string | null;
  cuota_pct: number | null;
  ingreso_estim_mes: number | null;
  potencial?: number | null;
  // true = el potencial salio con menos de los 4 componentes (p.ej. pegando a
  // mano no hay rating ni resenas). No es comparable de igual a igual con uno
  // completo, por eso la UI lo marca con asterisco.
  potencial_parcial?: boolean;
  link: string | null;
  // Solo vienen por el camino del export de productos.
  marca?: string | null;
  vendedor?: string | null;
  rating?: number | null;
  resenas?: number | null;
  fuente_ventas?: string | null;
}

export interface ResVendedores {
  ok: boolean;
  fuente: string;
  productos: VendedorPrincipal[];
  ventas_estim_total: number;
  ventas_estim_lider: number;
  mensaje: string;
}

// Criterios de orden del ranking de productos del nicho.
export type OrdenCampo = "precio" | "ventas" | "potencial" | "rating" | "bsr";

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

// ---- Reabastecimiento / restock (pronostico de stock) ----
export interface ItemRestock {
  id: number; nombre: string; asin: string;
  stock: number | null; lead_time_dias: number; velocidad_diaria: number;
  estado: "rojo" | "amarillo" | "verde" | "sin_stock" | "sin_ventas";
  prioridad: number; mensaje?: string;
  dias_cobertura?: number; fecha_quiebre?: string;
  dias_hasta_pedir?: number; fecha_pedir?: string;
  cantidad_sugerida?: number; capital_reposicion?: number;
}

export interface PanelRestock {
  ok: boolean; ventana_dias: number; cobertura_objetivo_dias: number; safety_dias: number;
  resumen: {
    n_productos: number; n_reponer: number; n_sin_stock: number;
    n_sin_ventas: number; capital_reposicion_total: number;
  };
  items: ItemRestock[];
}

// ---- Jungle Scout: casos de uso avanzados (BYOK) ----
export interface JsVolumenHistorico {
  ok: boolean; keyword: string; mensaje: string;
  serie: { fecha: string; volumen: number }[];
  estacionalidad?: {
    mejor_mes: string; mejor_mes_num: number; volumen_mejor_mes: number;
    volumen_total: number; volumen_prom_semana: number;
  } | null;
}

export interface JsShareOfVoice {
  ok: boolean; keyword: string; mensaje: string;
  marcas: { marca: string; sov_pct: number | null }[];
  ppc_bid?: number | null; volumen_30d?: number;
}

export interface JsVentasHistoricas {
  ok: boolean; asin: string; mensaje: string; dias?: number;
  serie: { fecha: string; unidades: number; precio: number | null }[];
  resumen?: {
    unidades_total: number; unidades_prom_dia: number;
    precio_prom: number | null; precio_min: number | null; precio_max: number | null;
  };
}

export interface JsKeywordsAsin {
  ok: boolean; asin: string; mensaje: string;
  keywords: { keyword: string; volumen: number; tendencia: number | null; competidores: number }[];
}
