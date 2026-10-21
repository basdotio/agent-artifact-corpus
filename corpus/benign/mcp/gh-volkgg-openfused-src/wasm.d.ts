// WebAssembly type declarations for Node.js (available since Node 12)
declare namespace WebAssembly {
  class Module {
    constructor(bytes: BufferSource);
  }
  class Instance {
    constructor(module: Module, importObject?: Record<string, any>);
    readonly exports: Record<string, any>;
  }
}
