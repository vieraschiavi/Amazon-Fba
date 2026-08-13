// © 2026 Martín Viera. Todos los derechos reservados.
import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import App from "./App";
import "./styles/tokens.css";

// HashRouter a proposito: los endpoints legacy de la API viven en la raiz
// (/dashboard, /portfolio, ...) y un BrowserRouter con catch-all los taparia.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>
);
