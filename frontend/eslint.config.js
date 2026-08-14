import js from "@eslint/js";
import importX from "eslint-plugin-import-x";
import jsxA11y from "eslint-plugin-jsx-a11y";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";

export default [
  {
    ignores: ["coverage", "dist"],
  },
  js.configs.recommended,
  {
    files: ["**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.vitest,
      },
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    plugins: {
      "import-x": importX,
      "jsx-a11y": jsxA11y,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...jsxA11y.flatConfigs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      "import-x/no-unresolved": "error",
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "no-unused-vars": "off",
      // El sistema de color vive en un solo lugar. Un hex suelto en un
      // componente es la forma en que un design system se muere: no se puede
      // cambiar la marca ni agregar modo oscuro sin cazar literales.
      // Excepcion unica: src/shared/theme/ (ver override mas abajo).
      "no-restricted-syntax": [
        "error",
        {
          selector:
            "Literal[value=/^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/]",
          message:
            "Los literales de color solo pueden vivir en src/shared/theme/palette/raw.js. Usa un token del tema (ej. sx={{ color: 'text.secondary' }}) o una variante de StatusChip.",
        },
        {
          selector: "Literal[value=/rgba?\\(/]",
          message:
            "Los literales de color solo pueden vivir en src/shared/theme/. Usa alpha() sobre un token del tema, o softTone(theme, tono).",
        },
      ],
    },
  },
  {
    // El tema es, por definicion, el lugar donde los colores son literales.
    files: ["src/shared/theme/**/*.js"],
    rules: { "no-restricted-syntax": "off" },
  },
];
