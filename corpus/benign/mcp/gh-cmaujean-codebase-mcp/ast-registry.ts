import { ASTParser, ASTParserRegistry, ParseResult } from './ast-types.js';

export class DefaultASTParserRegistry implements ASTParserRegistry {
  private parsers: ASTParser[] = [];

  registerParser(parser: ASTParser): void {
    this.parsers.push(parser);
  }

  getParser(filePath: string, extension: string): ASTParser | null {
    for (const parser of this.parsers) {
      if (parser.canParse(filePath, extension)) {
        return parser;
      }
    }
    return null;
  }

  async parseFile(content: string, filePath: string): Promise<ParseResult> {
    const extension = filePath.split('.').pop()?.toLowerCase() || '';
    const parser = this.getParser(filePath, extension);
    
    if (!parser) {
      return {
        success: false,
        error: `No parser available for file: ${filePath} (extension: ${extension})`
      };
    }

    try {
      return await parser.parse(content, filePath);
    } catch (error) {
      return {
        success: false,
        error: `Parse error for ${filePath}: ${error instanceof Error ? error.message : String(error)}`
      };
    }
  }
}