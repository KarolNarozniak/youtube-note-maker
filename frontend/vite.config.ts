import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, repoRoot, "");
  const frontendHost = env.FRONTEND_HOST || "127.0.0.1";
  const frontendPort = Number(env.FRONTEND_PORT || 2001);
  const backendHost = env.APP_HOST || "127.0.0.1";
  const backendPort = Number(env.APP_PORT || 2002);

  return {
    plugins: [react()],
    server: {
      host: frontendHost,
      port: frontendPort,
      proxy: {
        "/api": `http://${backendHost}:${backendPort}`
      }
    }
  };
});
