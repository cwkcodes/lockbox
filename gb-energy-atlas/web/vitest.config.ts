import path from "node:path";
import { defineConfig } from "vitest/config";

// Unit tests live beside the code; Playwright specs in ./e2e are run separately (npm run test:e2e).
export default defineConfig({
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  test: { include: ["src/**/*.test.ts"], environment: "node" },
});
