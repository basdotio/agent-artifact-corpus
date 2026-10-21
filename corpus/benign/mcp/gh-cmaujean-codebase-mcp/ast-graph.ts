import { CodeGraph, FileAST, ASTNode, Symbol, Dependency, SymbolReference } from './ast-types.js';

export class ASTGraphBuilder {
  private graph: CodeGraph;

  constructor() {
    this.graph = {
      nodes: new Map(),
      symbols: new Map(),
      dependencies: [],
      files: new Map()
    };
  }

  addFile(fileAST: FileAST): void {
    this.graph.files.set(fileAST.filePath, fileAST);
    
    // Add nodes to graph
    this.addNodeToGraph(fileAST.ast);
    
    // Add symbols to graph
    fileAST.symbols.forEach(symbol => {
      this.graph.symbols.set(symbol.id, symbol);
    });
    
    // Add dependencies to graph
    this.graph.dependencies.push(...fileAST.dependencies);
    
    // Build cross-references
    this.buildCrossReferences();
  }

  removeFile(filePath: string): void {
    const fileAST = this.graph.files.get(filePath);
    if (!fileAST) return;

    // Remove file from files map
    this.graph.files.delete(filePath);
    
    // Remove all symbols from this file
    fileAST.symbols.forEach(symbol => {
      this.graph.symbols.delete(symbol.id);
    });
    
    // Remove all nodes from this file
    this.removeNodeFromGraph(fileAST.ast);
    
    // Remove dependencies from this file
    this.graph.dependencies = this.graph.dependencies.filter(
      dep => dep.from !== filePath
    );
    
    // Rebuild cross-references since dependencies changed
    this.buildCrossReferences();
  }

  private addNodeToGraph(node: ASTNode): void {
    this.graph.nodes.set(node.id, node);
    node.children.forEach(child => this.addNodeToGraph(child));
  }

  private removeNodeFromGraph(node: ASTNode): void {
    this.graph.nodes.delete(node.id);
    node.children.forEach(child => this.removeNodeFromGraph(child));
  }

  private buildCrossReferences(): void {
    // Build symbol references across files
    for (const [filePath, fileAST] of this.graph.files) {
      for (const symbol of fileAST.symbols) {
        this.findSymbolReferences(symbol);
      }
    }
  }

  private findSymbolReferences(symbol: Symbol): void {
    const references: SymbolReference[] = [];
    
    // Add definition reference
    references.push({
      filePath: symbol.filePath,
      location: symbol.location,
      type: 'definition'
    });

    // Find usages across all files
    for (const [filePath, fileAST] of this.graph.files) {
      // Skip if it's the same file and same symbol (definition)
      if (filePath === symbol.filePath) {
        continue;
      }
      
      // Look for imports of this symbol
      for (const otherSymbol of fileAST.symbols) {
        if (otherSymbol.type === 'import' && 
            otherSymbol.imports?.source && 
            this.isSymbolFromFile(otherSymbol.imports.source, symbol.filePath) &&
            (otherSymbol.imports.importName === symbol.name || 
             otherSymbol.imports.importedAs === symbol.name)) {
          references.push({
            filePath: otherSymbol.filePath,
            location: otherSymbol.location,
            type: 'import'
          });
        }
      }
    }

    symbol.references = references;
  }

  private isSymbolFromFile(importSource: string, targetFilePath: string): boolean {
    // Simple heuristic - in a real implementation, you'd resolve module paths
    // This checks for relative imports that might point to the target file
    if (importSource.startsWith('./') || importSource.startsWith('../')) {
      return targetFilePath.includes(importSource.replace(/\.(js|ts|jsx|tsx)$/, ''));
    }
    return false;
  }

  getGraph(): CodeGraph {
    return this.graph;
  }

  getSymbolsByType(type: Symbol['type']): Symbol[] {
    return Array.from(this.graph.symbols.values()).filter(symbol => symbol.type === type);
  }

  getSymbolByName(name: string): Symbol[] {
    return Array.from(this.graph.symbols.values()).filter(symbol => symbol.name === name);
  }

  getFileSymbols(filePath: string): Symbol[] {
    return Array.from(this.graph.symbols.values()).filter(symbol => symbol.filePath === filePath);
  }

  getDependencyGraph(): Map<string, string[]> {
    const depGraph = new Map<string, string[]>();
    
    for (const dep of this.graph.dependencies) {
      if (!depGraph.has(dep.from)) {
        depGraph.set(dep.from, []);
      }
      depGraph.get(dep.from)!.push(dep.to);
    }
    
    return depGraph;
  }

  getSymbolsByFile(): Map<string, Symbol[]> {
    const symbolsByFile = new Map<string, Symbol[]>();
    
    for (const [_, symbol] of this.graph.symbols) {
      if (!symbolsByFile.has(symbol.filePath)) {
        symbolsByFile.set(symbol.filePath, []);
      }
      symbolsByFile.get(symbol.filePath)!.push(symbol);
    }
    
    return symbolsByFile;
  }

  findSymbolReferencesAcrossProject(symbolName: string): SymbolReference[] {
    const references: SymbolReference[] = [];
    
    for (const [_, symbol] of this.graph.symbols) {
      if (symbol.name === symbolName) {
        references.push(...symbol.references);
      }
    }
    
    return references;
  }

  getCallGraph(): Map<string, string[]> {
    const callGraph = new Map<string, string[]>();
    
    // This would require more sophisticated AST analysis to track function calls
    // For now, we'll return the dependency graph as a approximation
    return this.getDependencyGraph();
  }

  getExportedSymbols(): Map<string, Symbol[]> {
    const exportsByFile = new Map<string, Symbol[]>();
    
    for (const [_, symbol] of this.graph.symbols) {
      if (symbol.exports) {
        if (!exportsByFile.has(symbol.filePath)) {
          exportsByFile.set(symbol.filePath, []);
        }
        exportsByFile.get(symbol.filePath)!.push(symbol);
      }
    }
    
    return exportsByFile;
  }

  getImportedSymbols(): Map<string, Symbol[]> {
    const importsByFile = new Map<string, Symbol[]>();
    
    for (const [_, symbol] of this.graph.symbols) {
      if (symbol.imports) {
        if (!importsByFile.has(symbol.filePath)) {
          importsByFile.set(symbol.filePath, []);
        }
        importsByFile.get(symbol.filePath)!.push(symbol);
      }
    }
    
    return importsByFile;
  }

  generateGraphSummary(): {
    totalNodes: number;
    totalSymbols: number;
    totalFiles: number;
    symbolsByType: Record<string, number>;
    dependencyCount: number;
  } {
    const symbolsByType: Record<string, number> = {};
    
    for (const [_, symbol] of this.graph.symbols) {
      symbolsByType[symbol.type] = (symbolsByType[symbol.type] || 0) + 1;
    }
    
    return {
      totalNodes: this.graph.nodes.size,
      totalSymbols: this.graph.symbols.size,
      totalFiles: this.graph.files.size,
      symbolsByType,
      dependencyCount: this.graph.dependencies.length
    };
  }
}