/**
 * 统一的提示框工具函数
 * 替换原生 alert, confirm, prompt
 */
import React from 'react';
import { toast } from 'sonner';
import { CheckCircle2, XCircle, Info, AlertTriangle } from 'lucide-react';

/**
 * 显示成功提示
 */
export function showSuccess(message: string, title?: string) {
  toast.success(title || '成功', {
    description: message,
    duration: 3000,
    icon: <CheckCircle2 className="w-5 h-5 text-green-600" />,
  });
}

/**
 * 显示错误提示
 */
export function showError(message: string, title?: string) {
  toast.error(title || '错误', {
    description: message,
    duration: 5000,
    icon: <XCircle className="w-5 h-5 text-red-600" />,
  });
}

/**
 * 显示信息提示
 */
export function showInfo(message: string, title?: string) {
  toast.info(title || '信息', {
    description: message,
    duration: 3000,
    icon: <Info className="w-5 h-5 text-blue-600" />,
  });
}

/**
 * 显示警告提示
 */
export function showWarning(message: string, title?: string) {
  toast.warning(title || '警告', {
    description: message,
    duration: 4000,
    icon: <AlertTriangle className="w-5 h-5 text-yellow-600" />,
  });
}
