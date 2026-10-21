declare module 'sqlite3' {
  export interface RunResult {
    lastID: number;
    changes: number;
  }

  export interface Database {
    all(sql: string, params: any[], callback: (err: Error | null, rows: any[]) => void): void;
    all(sql: string, callback: (err: Error | null, rows: any[]) => void): void;
    
    get(sql: string, params: any[], callback: (err: Error | null, row: any) => void): void;
    get(sql: string, callback: (err: Error | null, row: any) => void): void;
    
    run(sql: string, params: any[], callback?: (err: Error | null) => void): this;
    run(sql: string, callback?: (err: Error | null) => void): this;
    
    exec(sql: string, callback?: (err: Error | null) => void): this;
    
    close(callback?: (err: Error | null) => void): void;
  }

  export class Statement {
    bind(params: any[]): this;
    reset(): this;
    finalize(callback?: (err: Error | null) => void): void;
  }

  export function verbose(): any;

  export class Database {
    constructor(filename: string, mode?: number, callback?: (err: Error | null) => void);
    constructor(filename: string, callback?: (err: Error | null) => void);
  }
} 