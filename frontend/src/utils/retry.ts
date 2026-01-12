/**
 * 重试工具
 * 提供带指数退避的重试机制
 */

interface RetryOptions {
  maxAttempts?: number;
  baseDelay?: number;
  maxDelay?: number;
  exponentialBase?: number;
  jitter?: boolean;
  onRetry?: (error: Error, attempt: number) => void;
}

/**
 * 重试异步函数
 */
export async function retry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const {
    maxAttempts = 3,
    baseDelay = 1000,
    maxDelay = 60000,
    exponentialBase = 2,
    jitter = true,
    onRetry,
  } = options;

  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      if (attempt === maxAttempts) {
        console.error(`重试 ${maxAttempts} 次后仍然失败:`, lastError);
        throw lastError;
      }

      // 计算延迟时间（指数退避）
      let delay = Math.min(
        baseDelay * Math.pow(exponentialBase, attempt - 1),
        maxDelay
      );

      // 添加随机抖动
      if (jitter) {
        delay = delay * (0.5 + Math.random());
      }

      console.warn(
        `第 ${attempt} 次尝试失败: ${lastError.message}，${Math.round(delay)}ms 后重试...`
      );

      if (onRetry) {
        onRetry(lastError, attempt);
      }

      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError || new Error('重试失败');
}

/**
 * 重试装饰器（用于类方法）
 */
export function Retryable(options: RetryOptions = {}) {
  return function (
    target: unknown,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: unknown[]) {
      return retry(() => originalMethod.apply(this, args), options);
    };

    return descriptor;
  };
}
