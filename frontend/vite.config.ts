import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const BASE_PATH = "/murder-mystery";

export default defineConfig({
  base: `${BASE_PATH}/`,
  plugins: [react()],
  server: {
    proxy: {
      [`${BASE_PATH}/api`]: {
        target: "http://localhost:8000",
        ws: true,
        rewrite: (path) => path.replace(new RegExp(`^${BASE_PATH}`), ""),
      },
    },
  },
});
