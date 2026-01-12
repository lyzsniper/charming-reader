/**
 * 统一的提示框工具函数
 * 替换原生 alert, confirm, prompt
 */
import { toast } from 'sonner';

/**
 * 显示成功提示
 */
export function showSuccess(message: string, title?: string) {
  toast.success(title || '成功', {
    description: message,
    duration: 3000,
  });
}

/**
 * 显示错误提示
 */
export function showError(message: string, title?: string) {
  toast.error(title || '错误', {
    description: message,
    duration: 5000,
  });
}

/**
 * 显示信息提示
 */
export function showInfo(message: string, title?: string) {
  toast.info(title || '提示', {
    description: message,
    duration: 3000,
  });
}

/**
 * 显示警告提示
 */
export function showWarning(message: string, title?: string) {
  toast.warning(title || '警告', {
    description: message,
    duration: 4000,
  });
}
