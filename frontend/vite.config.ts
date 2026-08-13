// © 2026 Martín Viera. Todos los derechos reservados.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// El SPA se sirve desde FastAPI (app.py) en el mismo origen que la API, asi
// que en produccion los fetch son relativos. En dev, `npm run dev` proxya
// /api y los endpoints legacy hacia uvicorn en 127.0.0.1:8000.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "./",
  build: { outDir: "dist" },
  server: {
    proxy: Object.fromEntries(
      ["/api", "/health", "/dashboard", "/portfolio", "/ganancias",
       "/dedicacion", "/mercado", "/assistant", "/webhook", "/creativos",
       "/motor", "/exito", "/publicar", "/run"].map((p) => [
        p, { target: "http://127.0.0.1:8000", changeOrigin: true },
      ])
    ),
  },
});
