import { parse } from '@babel/parser';
import traverse, { NodePath } from '@babel/traverse';
import * as t from '@babel/types';
import { 
  ASTParser, 
  ParseResult, 
  ASTNode, 
  Symbol, 
  Dependency, 
  SymbolReference, 
  ExportInfo, 
  ImportInfo 
} from './ast-types.js';

export class JavaScriptTypeScriptParser implements ASTParser {
  canParse(filePath: string, extension: string): boolean {
    return ['js', 'jsx', 'ts', 'tsx', 'mjs', 'cjs'].includes(extension);
  }

  async parse(content: string, filePath: string): Promise<ParseResult> {
    try {
      const isTypeScript = filePath.endsWith('.ts') || filePath.endsWith('.tsx');
      const isJSX = filePath.endsWith('.jsx') || filePath.endsWith('.tsx');

      const ast = parse(content, {
        sourceType: 'module',
        allowImportExportEverywhere: true,
        allowReturnOutsideFunction: true,
        plugins: [
          'asyncGenerators',
          'bigInt',
          'classProperties',
          'doExpressions',
          'dynamicImport',
          'exportDefaultFrom',
          'exportNamespaceFrom',
          'functionBind',
          'functionSent',
          'importMeta',
          'nullishCoalescingOperator',
          'numericSeparator',
          'objectRestSpread',
          'optionalCatchBinding',
          'optionalChaining',
          'throwExpressions',
          'topLevelAwait',
          'trailingFunctionCommas',
          ...(isJSX ? ['jsx'] : []),
          ...(isTypeScript ? ['typescript', ['decorators', { decoratorsBeforeExport: false }]] : ['decorators-legacy'])
        ]
      });

      const symbols: Symbol[] = [];
      const dependencies: Dependency[] = [];
      let nodeIdCounter = 0;

      const createASTNode = (node: t.Node, name?: string): ASTNode => {
        const id = `${filePath}:${nodeIdCounter++}`;
        return {
          id,
          type: node.type,
          name,
          location: {
            filePath,
            start: { line: node.loc?.start.line || 0, column: node.loc?.start.column || 0 },
            end: { line: node.loc?.end.line || 0, column: node.loc?.end.column || 0 }
          },
          children: [],
          metadata: {}
        };
      };

      const createSymbol = (
        name: string, 
        type: Symbol['type'], 
        node: t.Node,
        metadata: Record<string, any> = {}
      ): Symbol => {
        const id = `${filePath}:${name}:${type}:${node.loc?.start.line}`;
        return {
          id,
          name,
          type,
          filePath,
          location: {
            start: { line: node.loc?.start.line || 0, column: node.loc?.start.column || 0 },
            end: { line: node.loc?.end.line || 0, column: node.loc?.end.column || 0 }
          },
          references: [],
          metadata
        };
      };

      const rootNode = createASTNode(ast, 'Program');

      traverse(ast, {
        // Function declarations
        FunctionDeclaration(path: NodePath<t.FunctionDeclaration>) {
          if (path.node.id?.name) {
            const symbol = createSymbol(path.node.id.name, 'function', path.node, {
              async: path.node.async,
              generator: path.node.generator,
              params: path.node.params.length
            });
            symbols.push(symbol);
          }
        },

        // Arrow functions and function expressions
        VariableDeclarator(path: NodePath<t.VariableDeclarator>) {
          if (t.isIdentifier(path.node.id) && 
              (t.isArrowFunctionExpression(path.node.init) || t.isFunctionExpression(path.node.init))) {
            const symbol = createSymbol(path.node.id.name, 'function', path.node, {
              type: 'arrow',
              async: path.node.init.async,
              generator: t.isFunctionExpression(path.node.init) ? path.node.init.generator : false
            });
            symbols.push(symbol);
          } else if (t.isIdentifier(path.node.id)) {
            // Regular variables
            const symbol = createSymbol(path.node.id.name, 'variable', path.node);
            symbols.push(symbol);
          }
        },

        // Class declarations
        ClassDeclaration(path: NodePath<t.ClassDeclaration>) {
          if (path.node.id?.name) {
            const methods = path.node.body.body
              .filter(member => t.isClassMethod(member))
              .map(member => {
                if (t.isClassMethod(member) && t.isIdentifier(member.key)) {
                  return member.key.name;
                }
                return 'unknown';
              });

            const symbol = createSymbol(path.node.id.name, 'class', path.node, {
              superClass: path.node.superClass ? 
                (t.isIdentifier(path.node.superClass) ? path.node.superClass.name : 'unknown') : null,
              methods
            });
            symbols.push(symbol);
          }
        },

        // TypeScript interfaces
        TSInterfaceDeclaration(path: NodePath<t.TSInterfaceDeclaration>) {
          const symbol = createSymbol(path.node.id.name, 'interface', path.node, {
            extends: path.node.extends?.map(ext => 
              t.isIdentifier(ext.expression) ? ext.expression.name : 'unknown'
            ) || []
          });
          symbols.push(symbol);
        },

        // TypeScript type aliases
        TSTypeAliasDeclaration(path: NodePath<t.TSTypeAliasDeclaration>) {
          const symbol = createSymbol(path.node.id.name, 'type', path.node);
          symbols.push(symbol);
        },

        // Import declarations
        ImportDeclaration(path: NodePath<t.ImportDeclaration>) {
          const source = path.node.source.value;
          const specifiers: string[] = [];

          path.node.specifiers.forEach(spec => {
            let importName: string;
            let importedAs: string;
            let isDefault = false;

            if (t.isImportDefaultSpecifier(spec)) {
              importName = 'default';
              importedAs = spec.local.name;
              isDefault = true;
            } else if (t.isImportSpecifier(spec)) {
              importName = t.isIdentifier(spec.imported) ? spec.imported.name : 'unknown';
              importedAs = spec.local.name;
            } else if (t.isImportNamespaceSpecifier(spec)) {
              importName = '*';
              importedAs = spec.local.name;
            } else {
              return;
            }

            specifiers.push(importedAs);

            const symbol = createSymbol(importedAs, 'import', path.node);
            symbol.imports = {
              source,
              isDefault,
              importName,
              importedAs
            };
            symbols.push(symbol);
          });

          dependencies.push({
            from: filePath,
            to: source,
            type: 'import',
            specifiers
          });
        },

        // Export declarations
        ExportNamedDeclaration(path: NodePath<t.ExportNamedDeclaration>) {
          if (path.node.declaration) {
            // export const foo = ...
            // export function foo() {}
            // export class Foo {}
            if (t.isFunctionDeclaration(path.node.declaration) && path.node.declaration.id) {
              const symbol = createSymbol(path.node.declaration.id.name, 'export', path.node);
              symbol.exports = { isDefault: false, exportName: path.node.declaration.id.name };
              symbols.push(symbol);
            } else if (t.isClassDeclaration(path.node.declaration) && path.node.declaration.id) {
              const symbol = createSymbol(path.node.declaration.id.name, 'export', path.node);
              symbol.exports = { isDefault: false, exportName: path.node.declaration.id.name };
              symbols.push(symbol);
            } else if (t.isVariableDeclaration(path.node.declaration)) {
              path.node.declaration.declarations.forEach(decl => {
                if (t.isIdentifier(decl.id)) {
                  const symbol = createSymbol(decl.id.name, 'export', path.node);
                  symbol.exports = { isDefault: false, exportName: decl.id.name };
                  symbols.push(symbol);
                }
              });
            }
          } else if (path.node.specifiers) {
            // export { foo, bar }
            path.node.specifiers.forEach(spec => {
              if (t.isExportSpecifier(spec)) {
                const exportName = t.isIdentifier(spec.exported) ? spec.exported.name : 'unknown';
                const localName = t.isIdentifier(spec.local) ? spec.local.name : 'unknown';
                
                const symbol = createSymbol(localName, 'export', path.node);
                symbol.exports = { 
                  isDefault: false, 
                  exportName,
                  exportedAs: exportName !== localName ? exportName : undefined
                };
                symbols.push(symbol);
              }
            });
          }
        },

        // Export default declarations
        ExportDefaultDeclaration(path: NodePath<t.ExportDefaultDeclaration>) {
          let name = 'default';
          
          if (t.isFunctionDeclaration(path.node.declaration) && path.node.declaration.id) {
            name = path.node.declaration.id.name;
          } else if (t.isClassDeclaration(path.node.declaration) && path.node.declaration.id) {
            name = path.node.declaration.id.name;
          } else if (t.isIdentifier(path.node.declaration)) {
            name = path.node.declaration.name;
          }

          const symbol = createSymbol(name, 'export', path.node);
          symbol.exports = { isDefault: true, exportName: name };
          symbols.push(symbol);
        }
      });

      return {
        success: true,
        ast: rootNode,
        symbols,
        dependencies
      };

    } catch (error) {
      return {
        success: false,
        error: `Failed to parse ${filePath}: ${error instanceof Error ? error.message : String(error)}`
      };
    }
  }
}