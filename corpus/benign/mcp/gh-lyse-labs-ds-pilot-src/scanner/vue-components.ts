import { readFileSync } from "fs";
import { parse as parseSFC } from "@vue/compiler-sfc";
import { Project, SyntaxKind, type InterfaceDeclaration, type TypeAliasDeclaration, type TypeLiteralNode } from "ts-morph";

import type { PropInfo } from "./components.js";
import { parseVariants } from "./components.js";

export function parseVueProps(filePath: string, componentName: string): PropInfo[] {
  const content = readFileSync(filePath, "utf-8");
  const { descriptor } = parseSFC(content, { filename: filePath });

  const scriptSetup = descriptor.scriptSetup;
  if (!scriptSetup) return [];

  const scriptContent = scriptSetup.content;
  const project = new Project({ skipAddingFilesFromTsConfig: true });
  const sourceFile = project.createSourceFile(`${componentName}.ts`, scriptContent, { overwrite: true });

  const propsInterface = findDefinePropsInterface(sourceFile);
  if (!propsInterface) return [];

  const props = extractProps(propsInterface);

  const defaults = extractWithDefaults(sourceFile);
  for (const prop of props) {
    const def = defaults.get(prop.name);
    if (def) {
      prop.defaultValue = def;
    }
  }

  return props;
}

function findDefinePropsInterface(
  sourceFile: ReturnType<Project["createSourceFile"]>
): InterfaceDeclaration | TypeAliasDeclaration | undefined {
  const callExpressions = sourceFile.getDescendantsOfKind(SyntaxKind.CallExpression);

  for (const call of callExpressions) {
    const text = call.getExpression().getText();
    if (text !== "defineProps" && text !== "withDefaults") continue;

    let definePropsCall = call;
    if (text === "withDefaults") {
      const innerCall = call.getArguments()[0];
      if (!innerCall || innerCall.getKind() !== SyntaxKind.CallExpression) continue;
      definePropsCall = innerCall.asKindOrThrow(SyntaxKind.CallExpression);
    }

    const typeArgs = definePropsCall.getTypeArguments();
    if (typeArgs.length === 0) continue;

    const typeArgText = typeArgs[0].getText();

    const iface = sourceFile.getInterface(typeArgText);
    if (iface) return iface;

    const alias = sourceFile.getTypeAlias(typeArgText);
    if (alias) return alias;

    // Inline type: defineProps<{ label: string }>()
    if (typeArgs[0].getKind() === SyntaxKind.TypeLiteral) {
      const tempAlias = sourceFile.addTypeAlias({
        name: "__InlineProps",
        type: typeArgs[0].getText(),
      });
      return tempAlias;
    }
  }

  return undefined;
}

function extractProps(decl: InterfaceDeclaration | TypeAliasDeclaration): PropInfo[] {
  if (decl.getKind() === SyntaxKind.InterfaceDeclaration) {
    const iface = decl as InterfaceDeclaration;
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

  if (decl.getKind() === SyntaxKind.TypeAliasDeclaration) {
    const alias = decl as TypeAliasDeclaration;
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

  return [];
}

function extractWithDefaults(sourceFile: ReturnType<Project["createSourceFile"]>): Map<string, string> {
  const defaults = new Map<string, string>();

  const callExpressions = sourceFile.getDescendantsOfKind(SyntaxKind.CallExpression);
  for (const call of callExpressions) {
    if (call.getExpression().getText() !== "withDefaults") continue;

    const args = call.getArguments();
    if (args.length < 2) continue;

    const defaultsArg = args[1];
    if (defaultsArg.getKind() !== SyntaxKind.ObjectLiteralExpression) continue;

    const obj = defaultsArg.asKindOrThrow(SyntaxKind.ObjectLiteralExpression);
    for (const prop of obj.getProperties()) {
      if (prop.getKind() === SyntaxKind.PropertyAssignment) {
        const assignment = prop.asKindOrThrow(SyntaxKind.PropertyAssignment);
        defaults.set(assignment.getName(), assignment.getInitializerOrThrow().getText());
      }
    }
  }

  return defaults;
}
