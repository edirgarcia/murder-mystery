import { defineConfig, Plugin } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

function multiSpaFallback(): Plugin {
  return {
    name: "multi-spa-fallback",
    configureServer(server) {
      // Runs before Vite's built-in SPA fallback.
      // Rewrite /murder-mystery/* and /funny-questions/* to their HTML entry files
      // so Vite serves the right SPA shell for each game.
      server.middlewares.use((req, _res, next) => {
        const url = req.url || "";
        // Skip API calls (handled by proxy), static assets, and Vite internals
        if (url.includes("/api/") || url.includes(".") || url.startsWith("/@")) {
          return next();
        }
        if (url.startsWith("/murder-mystery")) {
          req.url = "/murder-mystery.html";
        } else if (url.startsWith("/funny-questions")) {
          req.url = "/funny-questions.html";
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), multiSpaFallback()],
  resolve: {
    alias: {
      "@shared": path.resolve(__dirname, "src/shared"),
    },
  },
  build: {
    rollupOptions: {
      input: {
        "murder-mystery": path.resolve(__dirname, "murder-mystery.html"),
        "funny-questions": path.resolve(__dirname, "funny-questions.html"),
      },
    },
  },
  server: {
    proxy: {
      "/murder-mystery/api": {
        target: "http://localhost:8000",
        ws: true,
        rewrite: (p) => p.replace(/^\/murder-mystery/, ""),
      },
      "/funny-questions/api": {
        target: "http://localhost:8000",
        ws: true,
        rewrite: (p) => p.replace(/^\/funny-questions/, ""),
      },
    },
  },
});
