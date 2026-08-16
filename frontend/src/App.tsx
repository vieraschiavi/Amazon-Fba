// © 2026 Martín Viera. Todos los derechos reservados.
import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Spinner } from "./components/ui";
import { useApp } from "./stores/app";
import { GateDemo } from "./pages/GateDemo";
import { Asistente } from "./pages/Asistente";
import { Alertas } from "./pages/Alertas";
import { Ayuda } from "./pages/Ayuda";
import { Config } from "./pages/Config";
import { Pricing } from "./pages/Pricing";
import { Portafolio } from "./pages/Portafolio";
import { Caja } from "./pages/Caja";
import { Ventas } from "./pages/Ventas";
import { Inventario } from "./pages/Inventario";
import { Inversores } from "./pages/Inversores";
import { Plan } from "./pages/Plan";
import { Investigacion } from "./pages/Investigacion";
import { Recomendador } from "./pages/Recomendador";
import { Mercado } from "./pages/Mercado";
import { JungleScout } from "./pages/JungleScout";
import { Herramientas } from "./pages/Herramientas";
import { Publicar } from "./pages/Publicar";

export default function App() {
  const { cargado, licencia, hidratar } = useApp();
  const idioma = useApp((s) => s.idioma);

  useEffect(() => { void hidratar(); }, [hidratar]);

  // El <html lang> tiene que seguir al idioma activo: index.html lo fija en
  // "es" y nada lo actualizaba, asi que en English/Portugues los lectores de
  // pantalla seguian usando pronunciacion española (WCAG 3.1.1).
  useEffect(() => { document.documentElement.lang = idioma; }, [idioma]);

  if (!cargado) {
    return <div className="h-full flex items-center justify-center"><Spinner texto="MV FBA IA" /></div>;
  }
  if (licencia && !licencia.vigente) {
    return <GateDemo estado={licencia} />;
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/recomendador" replace />} />
        <Route path="/recomendador" element={<Recomendador />} />
        <Route path="/investigacion" element={<Investigacion />} />
        <Route path="/mercado" element={<Mercado />} />
        <Route path="/jungle-scout" element={<JungleScout />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/portafolio" element={<Portafolio />} />
        <Route path="/publicar" element={<Publicar />} />
        <Route path="/ventas" element={<Ventas />} />
        <Route path="/inventario" element={<Inventario />} />
        <Route path="/caja" element={<Caja />} />
        <Route path="/inversores" element={<Inversores />} />
        <Route path="/plan" element={<Plan />} />
        <Route path="/herramientas" element={<Herramientas />} />
        <Route path="/asistente" element={<Asistente />} />
        <Route path="/alertas" element={<Alertas />} />
        <Route path="/config" element={<Config />} />
        <Route path="/ayuda" element={<Ayuda />} />
        <Route path="*" element={<Navigate to="/recomendador" replace />} />
      </Routes>
    </Layout>
  );
}
