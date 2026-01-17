/**
 * Toast 组件 - 使用 sonner 实现
 * 更现代、更美观的 toast 通知
 */
import { Toaster as SonnerToaster } from 'sonner';

export function Toaster() {
  return (
    <SonnerToaster
      position="top-right"
      expand={true}
      richColors={false}
      closeButton={true}
      duration={3000}
      toastOptions={{
        classNames: {
          toast: 'group toast group-[.toaster]:bg-white group-[.toaster]:text-gray-950 group-[.toaster]:border group-[.toaster]:shadow-lg group-[.toaster]:rounded-xl group-[.toaster]:p-4',
          description: 'group-[.toast]:text-gray-600',
          actionButton: 'group-[.toast]:bg-gray-900 group-[.toast]:text-gray-50',
          cancelButton: 'group-[.toast]:bg-gray-100 group-[.toast]:text-gray-500',
          success: 'group-[.toaster]:bg-gradient-to-r group-[.toaster]:from-green-50 group-[.toaster]:to-emerald-50 group-[.toaster]:border-green-200 group-[.toaster]:shadow-green-100/50',
          error: 'group-[.toaster]:bg-gradient-to-r group-[.toaster]:from-red-50 group-[.toaster]:to-rose-50 group-[.toaster]:border-red-200 group-[.toaster]:shadow-red-100/50',
          info: 'group-[.toaster]:bg-gradient-to-r group-[.toaster]:from-blue-50 group-[.toaster]:to-cyan-50 group-[.toaster]:border-blue-200 group-[.toaster]:shadow-blue-100/50',
          warning: 'group-[.toaster]:bg-gradient-to-r group-[.toaster]:from-yellow-50 group-[.toaster]:to-amber-50 group-[.toaster]:border-yellow-200 group-[.toaster]:shadow-yellow-100/50',
        },
      }}
    />
  );
}
