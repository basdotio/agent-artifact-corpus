module.exports = {
  // --- Configuración global ---
  printWidth: 80,
  tabWidth: 2,
  useTabs: false,
  singleQuote: true,
  semi: true,
  trailingComma: "es5",

  // --- Configuración específica por tipo de archivo ---
  overrides: [
    {
      files: "*.md",
      options: {
        printWidth: 100,
        proseWrap: "always",
        tabWidth: 2,
        useTabs: false,
        singleQuote: false
      }
    }
  ]
};
