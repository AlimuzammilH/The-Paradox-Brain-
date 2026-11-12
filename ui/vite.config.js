import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// `npm run build` makes one self-contained HTML file (dist/index.html) that opens from anywhere.
export default defineConfig({
  base: "./",
  plugins: [viteSingleFile()],
  build: { chunkSizeWarningLimit: 2000 },
  server: { port: 5173 },
});
