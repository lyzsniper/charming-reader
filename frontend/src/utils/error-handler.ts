/**
 * 统一错误处理工具
 */

export interface APIError {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  data: null;
}

export interface APIResponse<T> {
  success: true;
  message?: string;
  data: T;
}

export class APIException extends Error {
  constructor(
    public code: string,
    message: string,
    public details?: Record<string, unknown>,
    public statusCode?: number
  ) {
    super(message);
    this.name = 'APIException';
  }

  static fromError(error: APIError, statusCode?: number): APIException {
    return new APIException(
      error.error.code,
      error.error.message,
      error.error.details,
      statusCode
    );
  }
}

/**
 * 解析 API 响应错误
 */
export function parseAPIError(error: unknown): APIException {
  if (error instanceof APIException) {
    return error;
  }

  if (error instanceof Error) {
    // 尝试从错误消息中解析 JSON
    try {
      const parsed = JSON.parse(error.message);
      if (parsed.error) {
        return APIException.fromError(parsed as APIError);
      }
    } catch {
      // 不是 JSON 格式，返回通用错误
    }
    return new APIException('UNKNOWN_ERROR', error.message);
  }

  return new APIException('UNKNOWN_ERROR', '未知错误');
}

/**
 * 获取用户友好的错误消息
 */
export function getErrorMessage(error: unknown): string {
  const apiError = parseAPIError(error);
  
  // 根据错误代码返回友好的中文消息
  const errorMessages: Record<string, string> = {
    VALIDATION_ERROR: '请求参数验证失败',
    NOT_FOUND: '请求的资源不存在',
    UNAUTHORIZED: '未授权访问，请先登录',
    FORBIDDEN: '没有权限执行此操作',
    INTERNAL_ERROR: '服务器内部错误，请稍后重试',
    NETWORK_ERROR: '网络连接失败，请检查网络设置',
    TIMEOUT_ERROR: '请求超时，请稍后重试',
  };

  return errorMessages[apiError.code] || apiError.message || '操作失败，请稍后重试';
}
