import { useEffect, useCallback } from 'react';

export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  shift?: boolean;
  alt?: boolean;
  action: () => void;
  description?: string;
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const keyMatches = event.key.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatches = shortcut.ctrl ? event.ctrlKey : !event.ctrlKey;
        const metaMatches = shortcut.meta ? event.metaKey : !event.metaKey;
        const shiftMatches = shortcut.shift ? event.shiftKey : !event.shiftKey;
        const altMatches = shortcut.alt ? event.altKey : !event.altKey;

        // 处理 Ctrl/Cmd 键：在 Mac 上使用 metaKey，在 Windows/Linux 上使用 ctrlKey
        const modifierMatches =
          shortcut.ctrl || shortcut.meta
            ? event.ctrlKey || event.metaKey
            : !event.ctrlKey && !event.metaKey;

        if (
          keyMatches &&
          modifierMatches &&
          shiftMatches &&
          altMatches &&
          !event.repeat
        ) {
          // 检查是否在输入框中
          const target = event.target as HTMLElement;
          const isInput =
            target.tagName === 'INPUT' ||
            target.tagName === 'TEXTAREA' ||
            target.isContentEditable;

          // 某些快捷键即使在输入框中也要生效
          const allowedInInput = ['Escape', 'Escape'].includes(shortcut.key);

          if (!isInput || allowedInInput) {
            event.preventDefault();
            shortcut.action();
            break;
          }
        }
      }
    },
    [shortcuts]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);
}

// 常用快捷键组合
export const COMMON_SHORTCUTS = {
  SEND_MESSAGE: { key: 'Enter', ctrl: true, description: '发送消息' },
  NEW_CHAT: { key: 'n', ctrl: true, description: '新对话' },
  ESCAPE: { key: 'Escape', description: '关闭/取消' },
  SEARCH: { key: 'k', ctrl: true, description: '搜索' },
  HELP: { key: '/', ctrl: true, description: '显示帮助' },
} as const;
