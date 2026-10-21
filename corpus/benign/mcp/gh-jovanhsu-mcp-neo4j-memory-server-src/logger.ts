// 日志级别枚举
export enum LogLevel {
  DEBUG = "debug",
  INFO = "info",
  WARN = "warning",
  ERROR = "error",
}

// 日志记录器接口
export interface Logger {
  debug(message: string, payload?: any): void;
  info(message: string, payload?: any): void;
  warn(message: string, payload?: any): void;
  error(message: string, payload?: any): void;
  setLevel(level: LogLevel): void;
}

// 空日志记录器实现
export class NullLogger implements Logger {
  debug(message: string, payload?: any): void {}
  info(message: string, payload?: any): void {}
  warn(message: string, payload?: any): void {}
  error(message: string, payload?: any): void {}
  setLevel(level: LogLevel): void {}
}

// 控制台日志记录器实现
export class ConsoleLogger implements Logger {
  private level: LogLevel = LogLevel.INFO;

  setLevel(level: LogLevel): void {
    this.level = level;
  }

  debug(message: string, payload?: any): void {
    if (this.shouldLog(LogLevel.DEBUG)) {
      console.debug(message, payload);
    }
  }

  info(message: string, payload?: any): void {
    if (this.shouldLog(LogLevel.INFO)) {
      console.info(message, payload);
    }
  }

  warn(message: string, payload?: any): void {
    if (this.shouldLog(LogLevel.WARN)) {
      console.warn(message, payload);
    }
  }

  error(message: string, payload?: any): void {
    if (this.shouldLog(LogLevel.ERROR)) {
      console.error(message, payload);
    }
  }

  private shouldLog(messageLevel: LogLevel): boolean {
    const levels = [
      LogLevel.DEBUG,
      LogLevel.INFO,
      LogLevel.WARN,
      LogLevel.ERROR,
    ];
    return levels.indexOf(messageLevel) >= levels.indexOf(this.level);
  }
}