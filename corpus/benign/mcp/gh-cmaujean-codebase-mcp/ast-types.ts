export interface ASTNode {
  id: string;
  type: string;
  name?: string;
  location: {
    filePath: string;
    start: { line: number; column: number };
    end: { line: number; column: number };
  };
  children: ASTNode[];
  metadata: Record<string, any>;
}

export interface Symbol {
  id: string;
  name: string;
  type: 'function' | 'class' | 'variable' | 'import' | 'export' | 'interface' | 'type';
  filePath: string;
  location: {
    start: { line: number; column: number };
    end: { line: number; column: number };
  };
  references: SymbolReference[];
  exports?: ExportInfo;
  imports?: ImportInfo;
  metadata: Record<string, any>;
}

export interface SymbolReference {
  filePath: string;
  location: {
    start: { line: number; column: number };
    end: { line: number; column: number };
  };
  type: 'definition' | 'usage' | 'call' | 'import' | 'export';
}

export interface ExportInfo {
  isDefault: boolean;
  exportName?: string;
  exportedAs?: string;
}

export interface ImportInfo {
  source: string;
  isDefault: boolean;
  importName?: string;
  importedAs?: string;
}

export interface Dependency {
  from: string;
  to: string;
  type: 'import' | 'require' | 'dynamic_import';
  specifiers: string[];
}

export interface CodeGraph {
  nodes: Map<string, ASTNode>;
  symbols: Map<string, Symbol>;
  dependencies: Dependency[];
  files: Map<string, FileAST>;
}

export interface FileAST {
  filePath: string;
  ast: ASTNode;
  symbols: Symbol[];
  dependencies: Dependency[];
  exports: Symbol[];
  imports: Symbol[];
}

export interface ParseResult {
  success: boolean;
  ast?: ASTNode;
  symbols?: Symbol[];
  dependencies?: Dependency[];
  error?: string;
}

export interface ASTParser {
  canParse(filePath: string, extension: string): boolean;
  parse(content: string, filePath: string): Promise<ParseResult>;
}

export interface ASTParserRegistry {
  registerParser(parser: ASTParser): void;
  getParser(filePath: string, extension: string): ASTParser | null;
  parseFile(content: string, filePath: string): Promise<ParseResult>;
}