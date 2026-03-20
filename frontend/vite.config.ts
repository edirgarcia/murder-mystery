import { defineConfig, Plugin } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

function multiSpaFallback(): Plugin {
  return {
    name: "multi-spa-fallback",
    configureServer(server) {
      // Runs before Vite's built-in SPA fallback.
      // Rewrite game routes to their HTML entry files.
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
        } else if (url.startsWith("/werewolf")) {
          req.url = "/werewolf.html";
        } else if (url.startsWith("/prisoners-dilemma")) {
          req.url = "/prisoners-dilemma.html";
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
        werewolf: path.resolve(__dirname, "werewolf.html"),
        "prisoners-dilemma": path.resolve(__dirname, "prisoners-dilemma.html"),
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
      "/werewolf/api": {
        target: "http://localhost:8000",
        ws: true,
        rewrite: (p) => p.replace(/^\/werewolf/, ""),
      },
      "/prisoners-dilemma/api": {
        target: "http://localhost:8000",
        ws: true,
        rewrite: (p) => p.replace(/^\/prisoners-dilemma/, ""),
      },
    },
  },
});
