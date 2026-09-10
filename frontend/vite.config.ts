import path from "node:path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    // The API lives on its own process; proxying keeps the browser same-origin.
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
  },
})
