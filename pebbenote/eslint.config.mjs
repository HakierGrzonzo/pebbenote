import js from "@eslint/js";
import prettier from "eslint-config-prettier";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "**/src/ts/api/**",
      "**/src/ts/env.ts",
      "**/src/ts-build/**",
      "**/build/**",
    ],
  },
  js.configs.recommended,
  tseslint.configs.recommended,
  {
    files: ["**/src/ts/**/*.ts"],
    languageOptions: {
      globals: {
        Pebble: "readonly",
        localStorage: "readonly",
        XMLHttpRequest: "readonly",
        require: "readonly",
      },
    },
  },
  {
    files: ["**/scripts/**/*.mjs"],
    languageOptions: { globals: globals.node },
  },
  prettier,
);
