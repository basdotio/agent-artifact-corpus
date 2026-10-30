declare function setIsStdio(isStdio: boolean): void;
/**
 * Log info message
 */
declare function info(message: string, ...args: unknown[]): void;
/**
 * Log warning message
 */
declare function warn(message: string, ...args: unknown[]): void;
/**
 * Log error message
 */
declare function error(message: string, error?: unknown): void;
/**
 * Log success message
 */
declare function success(message: string, ...args: unknown[]): void;
/**
 * Logger object for backward compatibility
 */
export declare const logger: {
    info: typeof info;
    warn: typeof warn;
    error: typeof error;
    success: typeof success;
    setIsStdio: typeof setIsStdio;
};
export {};
