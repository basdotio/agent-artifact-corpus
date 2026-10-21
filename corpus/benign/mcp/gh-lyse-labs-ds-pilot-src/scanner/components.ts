import { globSync } from "glob";
import { basename, resolve } from "path";
import { Project, SyntaxKind, type InterfaceDeclaration, type TypeAliasDeclaration, type TypeLiteralNode } from "ts-morph";
import { parseVueProps } from "./vue-components.js";

export interface ComponentInfo {
  name: string;
  filePath: string;
  exportType: "named" | "default";
}

export interface PropInfo {
  name: string;
  type: string;
  required: boolean;
  defaultValue?: string;
  variants?: string[];
}

export interface ComponentWithProps extends ComponentInfo {
  props: PropInfo[];
}

const IGNORED_PATTERNS = [
  "**/*.test.*",
  "**/*.spec.*",
  "**/*.stories.*",
  "**/*.d.ts",
  "**/index.ts",
  "**/index.tsx",
  "**/index.js",
  "**/index.jsx",
  "**/__tests__/**",
];

export function scanComponents(dir: string): ComponentInfo[] {
  const absDir = resolve(dir);
  const files = globSync("**/*.{tsx,ts,jsx,js,vue}", {
    cwd: absDir,
    absolute: true,
    ignore: IGNORED_PATTERNS,
  });

  const components: ComponentInfo[] = [];
  const project = new Project({ skipAddingFilesFromTsConfig: true });

  for (const file of files) {
    const name = basename(file).replace(/\.(tsx|ts|jsx|js|vue)$/, "");
    if (name[0] !== name[0].toUpperCase()) continue;

    if (file.endsWith(".vue")) {
      components.push({ name, filePath: file, exportType: "default" });
      continue;
    }

    const sourceFile = project.addSourceFileAtPath(file);

    const defaultExport = sourceFile.getDefaultExportSymbol();
    if (defaultExport) {
      components.push({ name, filePath: file, exportType: "default" });
      continue;
    }

    const namedExports = sourceFile.getExportedDeclarations();
    for (const [exportName, declarations] of namedExports) {
      if (exportName[0] === exportName[0].toUpperCase() && exportName !== "default") {
        const isTypeOnly = declarations.every(
          (d) =>
            d.getKind() === SyntaxKind.InterfaceDeclaration ||
            d.getKind() === SyntaxKind.TypeAliasDeclaration
        );
        if (isTypeOnly) continue;
        components.push({ name: exportName, filePath: file, exportType: "named" });
      }
    }
  }

  return components;
}

export function getComponentProps(filePath: string, componentName: string): PropInfo[] {
  if (filePath.endsWith(".vue")) {
    return parseVueProps(filePath, componentName);
  }

  const project = new Project({ skipAddingFilesFromTsConfig: true });
  const sourceFile = project.addSourceFileAtPath(filePath);

  const interfaces = sourceFile.getInterfaces();
  const typeAliases = sourceFile.getTypeAliases();

  const propsDecl = findPropsDeclaration(interfaces, typeAliases, componentName);
  if (!propsDecl) return [];

  let props: PropInfo[];
  if (propsDecl.getKind() === SyntaxKind.InterfaceDeclaration) {
    props = extractFromInterface(propsDecl as InterfaceDeclaration);
  } else if (propsDecl.getKind() === SyntaxKind.TypeAliasDeclaration) {
    props = extractFromTypeAlias(propsDecl as TypeAliasDeclaration);
  } else {
    return [];
  }

  const defaults = extractDefaults(sourceFile, componentName);
  for (const prop of props) {
    const def = defaults.get(prop.name);
    if (def) {
      prop.defaultValue = def;
    }
  }

  return props;
}

function findPropsDeclaration(
  interfaces: InterfaceDeclaration[],
  typeAliases: TypeAliasDeclaration[],
  componentName: string
): InterfaceDeclaration | TypeAliasDeclaration | undefined {
  const propsNames = [`${componentName}Props`, "Props"];

  for (const name of propsNames) {
    const iface = interfaces.find((i) => i.getName() === name);
    if (iface) return iface;

    const alias = typeAliases.find((t) => t.getName() === name);
    if (alias) return alias;
  }

  return undefined;
}

function extractDefaults(sourceFile: ReturnType<Project["addSourceFileAtPath"]>, componentName: string): Map<string, string> {
  const defaults = new Map<string, string>();

  for (const fn of sourceFile.getFunctions()) {
    if (fn.getName() !== componentName) continue;
    const param = fn.getParameters()[0];
    if (!param) continue;
    for (const el of param.getDescendantsOfKind(SyntaxKind.BindingElement)) {
      const init = el.getInitializer();
      if (init) defaults.set(el.getName(), init.getText());
    }
  }

  for (const varDecl of sourceFile.getVariableDeclarations()) {
    if (varDecl.getName() !== componentName) continue;
    const arrowFn = varDecl.getInitializerIfKind(SyntaxKind.ArrowFunction);
    if (!arrowFn) continue;
    const param = arrowFn.getParameters()[0];
    if (!param) continue;
    for (const el of param.getDescendantsOfKind(SyntaxKind.BindingElement)) {
      const init = el.getInitializer();
      if (init) defaults.set(el.getName(), init.getText());
    }
  }

  return defaults;
}

function extractFromInterface(iface: InterfaceDeclaration): PropInfo[] {
  return iface.getProperties().map((prop) => {
    const typeText = prop.getType().getText();
    const variants = parseVariants(typeText);
    return {
      name: prop.getName(),
      type: typeText,
      required: !prop.hasQuestionToken(),
      ...(variants && { variants }),
    };
  });
}

function extractFromTypeAlias(alias: TypeAliasDeclaration): PropInfo[] {
  const typeNode = alias.getTypeNode();
  if (!typeNode || typeNode.getKind() !== SyntaxKind.TypeLiteral) return [];

  const typeLiteral = typeNode as TypeLiteralNode;
  return typeLiteral.getProperties().map((prop) => {
    const typeText = prop.getType().getText();
    const variants = parseVariants(typeText);
    return {
      name: prop.getName(),
      type: typeText,
      required: !prop.hasQuestionToken(),
      ...(variants && { variants }),
    };
  });
}

export function parseVariants(typeText: string): string[] | undefined {
  const matches = typeText.match(/"([^"]+)"/g);
  if (!matches || matches.length < 2) return undefined;
  return matches.map((m) => m.replace(/"/g, ""));
}
