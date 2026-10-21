/**
 * 从错误对象中提取错误信息
 * @param error 错误对象
 * @returns 包含错误信息的对象
 */
export const extractError = (error: unknown): { message: string } => {
  if (error instanceof Error) {
    return {
      message: error.message,
    };
  } else {
    return {
      message: "Unknown error",
    };
  }
};

/**
 * 生成唯一ID
 * @returns 唯一ID字符串
 */
export const generateId = (): string => {
  return Math.random().toString(36).substring(2, 15) + 
         Math.random().toString(36).substring(2, 15);
};

/**
 * 格式化Cypher查询参数
 * @param params 参数对象
 * @returns 格式化后的参数对象
 */
export const formatCypherParams = (params: Record<string, any>): Record<string, any> => {
  const formattedParams: Record<string, any> = {};
  
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      formattedParams[key] = value;
    } else if (value === null || value === undefined) {
      formattedParams[key] = null;
    } else if (typeof value === 'object') {
      formattedParams[key] = formatCypherParams(value);
    } else {
      formattedParams[key] = value;
    }
  }
  
  return formattedParams;
};