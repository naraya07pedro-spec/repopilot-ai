import { defineConfig } from "vitest/config";
export default defineConfig({ test: { environment: "jsdom", globals: true, include: ["app/**/*.test.tsx", "components/**/*.test.tsx"], maxWorkers: 1 } });
