import js from "@eslint/js";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";

export default [
  {
    ignores: ["dist/**", "node_modules/**"],
  },
  js.configs.recommended,
  {
    files: ["**/*.{ts,tsx,js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        document: "readonly",
        window: "readonly",
        navigator: "readonly",
        Event: "readonly",
      },
    },
    plugins: {
      "react-hooks": reactHooks,
      "jsx-a11y": jsxA11y,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "jsx-a11y/control-has-associated-label": "warn",
      "jsx-a11y/label-has-associated-control": [
        "warn",
        {
          depth: 2,
        },
      ],
    },
  },
  {
    files: ["src/__tests__/**/*.{ts,tsx,js,jsx}", "src/test/**/*.{ts,tsx,js,jsx}"],
    languageOptions: {
      globals: {
        test: "readonly",
        expect: "readonly",
      },
    },
  },
];
