import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
    baseDirectory: __dirname,
});

const eslintConfig = [
    // Use only core-web-vitals for now to avoid circular deps in full set
    ...compat.extends("next/core-web-vitals"),
];

export default eslintConfig;
