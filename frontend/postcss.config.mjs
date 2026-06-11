import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));

const config = {
  plugins: {
    tailwindcss: { config: join(__dirname, "tailwind.config.js") },
    autoprefixer: {},
  },
};

export default config;
