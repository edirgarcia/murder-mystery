import { defineConfig, Plugin } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Every game is a separate SPA served under /<slug>/ from <slug>.html.
// Adding a game = adding its slug here (plus the backend GameRegistration).
const GAMES = [
  "murder-mystery",
  "funny-questions",
  "werewolf",
  "prisoners-dilemma",
  "basta",
  "trading-city",
];

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
        const game = GAMES.find((slug) => url.startsWith(`/${slug}`));
        if (game) {
          req.url = `/${game}.html`;
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
      input: Object.fromEntries(
        GAMES.map((slug) => [slug, path.resolve(__dirname, `${slug}.html`)])
      ),
    },
  },
  server: {
    proxy: Object.fromEntries(
      GAMES.map((slug) => [
        `/${slug}/api`,
        {
          target: "http://localhost:8000",
          ws: true,
          rewrite: (p: string) => p.replace(new RegExp(`^/${slug}`), ""),
        },
      ])
    ),
  },
});
