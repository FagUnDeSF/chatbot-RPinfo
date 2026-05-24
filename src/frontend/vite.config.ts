import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = {
    ...loadEnv(mode, path.resolve(process.cwd(), "../.."), ""),
    ...loadEnv(mode, process.cwd(), "")
  };
  const readEnv = (name: string): string | undefined =>
    Object.prototype.hasOwnProperty.call(env, name) ? env[name] : undefined;
  const internalUsername = readEnv("INTERNAL_AUTH_USERNAME") ?? "rp-direcao";
  const internalToken = readEnv("INTERNAL_AUTH_TOKEN") ?? readEnv("INTERNAL_AUTH_DIRECAO_TOKEN");

  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: false,
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
          configure(proxy) {
            proxy.on("proxyReq", (proxyReq) => {
              proxyReq.setHeader("X-Internal-Username", internalUsername);
              if (internalToken !== undefined && internalToken.trim() !== "") {
                proxyReq.setHeader("X-Internal-Token", internalToken);
              }
            });
          }
        }
      }
    },
    build: {
      sourcemap: false,
      target: "es2022"
    }
  };
});
