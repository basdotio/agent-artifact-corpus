import sqlite3 from "sqlite3";
import { DbAdapter } from "./adapter.js";

/**
 * SQLite database adapter implementation
 */
export class SqliteAdapter implements DbAdapter {
  private db: sqlite3.Database | null = null;
  private dbPath: string;

  constructor(dbPath: string) {
    this.dbPath = dbPath;
  }

  /**
   * Initialize the SQLite database connection
   */
  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      // Ensure the dbPath is accessible
      console.error(`[INFO] Opening SQLite database at: ${this.dbPath}`);
      this.db = new sqlite3.Database(this.dbPath, sqlite3.OPEN_READWRITE | sqlite3.OPEN_CREATE, (err) => {
        if (err) {
          console.error(`[ERROR] SQLite connection error: ${err.message}`);
          reject(err);
        } else {
          console.error("[INFO] SQLite database opened successfully");
          resolve();
        }
      });
    });
  }

  /**
   * Execute a SQL query and get all results
   * @param query SQL query to execute
   * @param params Query parameters
   * @returns Promise with query results
   */
  async all(query: string, params: any[] = []): Promise<any[]> {
    if (!this.db) {
      throw new Error("Database not initialized");
    }

    return new Promise((resolve, reject) => {
      this.db!.all(query, params, (err: Error | null, rows: any[]) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows);
        }
      });
    });
  }

  /**
   * Execute a SQL query that modifies data
   * @param query SQL query to execute
   * @param params Query parameters
   * @returns Promise with result info
   */
  async run(query: string, params: any[] = []): Promise<{ changes: number, lastID: number }> {
    if (!this.db) {
      throw new Error("Database not initialized");
    }

    return new Promise((resolve, reject) => {
      this.db!.run(query, params, function(this: sqlite3.RunResult, err: Error | null) {
        if (err) {
          reject(err);
        } else {
          resolve({ changes: this.changes, lastID: this.lastID });
        }
      });
    });
  }

  /**
   * Execute multiple SQL statements
   * @param query SQL statements to execute
   * @returns Promise that resolves when execution completes
   */
  async exec(query: string): Promise<void> {
    if (!this.db) {
      throw new Error("Database not initialized");
    }

    return new Promise((resolve, reject) => {
      this.db!.exec(query, (err: Error | null) => {
        if (err) {
          reject(err);
        } else {
          resolve();
        }
      });
    });
  }

  /**
   * Close the database connection
   */
  async close(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        resolve();
        return;
      }
      
      this.db.close((err: Error | null) => {
        if (err) {
          reject(err);
        } else {
          this.db = null;
          resolve();
        }
      });
    });
  }

  /**
   * Get database metadata
   */
  getMetadata(): { name: string, type: string, path: string } {
    return {
      name: "SQLite",
      type: "sqlite",
      path: this.dbPath
    };
  }

  /**
   * Get database-specific query for listing tables
   */
  getListTablesQuery(): string {
    return "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'";
  }

  /**
   * Get database-specific query for describing a table
   * @param tableName Table name
   */
  getDescribeTableQuery(tableName: string): string {
    return `PRAGMA table_info(${tableName})`;
  }
} 