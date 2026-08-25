import js from "@eslint/js";
import tsParser from "@typescript-eslint/parser";
import jsxA11y from "eslint-plugin-jsx-a11y";
import reactHooks from "eslint-plugin-react-hooks";

const browserGlobals = {
  document: "readonly",
  Event: "readonly",
  EventSource: "readonly",
  fetch: "readonly",
  HTMLUListElement: "readonly",
  MessageEvent: "readonly",
  navigator: "readonly",
  setTimeout: "readonly",
  window: "readonly",
};

const testGlobals = {
  afterEach: "readonly",
  beforeEach: "readonly",
  describe: "readonly",
  expect: "readonly",
  test: "readonly",
  vi: "readonly",
};

export default [
  {
    ignores: ["dist/**", "node_modules/**", "**/*.d.ts", "**/*.tsbuildinfo"],
  },
  js.configs.recommended,
  {
    files: ["**/*.{ts,tsx,js,jsx}"],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: browserGlobals,
    },
    plugins: {
      "jsx-a11y": jsxA11y,
      "react-hooks": reactHooks,
    },
    rules: {
      "no-unused-vars": "off",
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
        ...browserGlobals,
        ...testGlobals,
      },
    },
  },
];
