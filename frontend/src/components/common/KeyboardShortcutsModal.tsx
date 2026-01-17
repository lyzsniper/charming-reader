import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Keyboard } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { COMMON_SHORTCUTS } from '@/hooks/useKeyboardShortcuts';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const shortcuts = [
  {
    category: '通用',
    items: [
      { keys: ['Ctrl', 'K'], description: '打开搜索/命令面板' },
      { keys: ['Ctrl', '/'], description: '显示快捷键帮助' },
      { keys: ['Esc'], description: '关闭模态框/面板' },
    ],
  },
  {
    category: '对话',
    items: [
      { keys: ['Ctrl', 'Enter'], description: '发送消息' },
      { keys: ['Ctrl', 'N'], description: '新建对话' },
    ],
  },
  {
    category: '导航',
    items: [
      { keys: ['Ctrl', 'H'], description: '打开历史记录' },
      { keys: ['Ctrl', 'B'], description: '打开知识库' },
      { keys: ['Ctrl', ','], description: '打开设置' },
    ],
  },
];

const getKeyDisplay = (key: string) => {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  if (key === 'Ctrl' && isMac) return '⌘';
  if (key === 'Ctrl') return 'Ctrl';
  if (key === 'Alt' && isMac) return '⌥';
  if (key === 'Shift' && isMac) return '⇧';
  return key;
};

export const KeyboardShortcutsModal: React.FC<KeyboardShortcutsModalProps> = ({
  isOpen,
  onClose,
}) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed inset-0 m-auto w-full max-w-2xl h-fit max-h-[80vh] bg-white rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col"
          >
            <div className="p-6 border-b flex items-center justify-between bg-gradient-to-r from-gray-50 to-white">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                  <Keyboard className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold">键盘快捷键</h2>
                  <p className="text-sm text-gray-500">提高你的工作效率</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="w-5 h-5" />
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-6">
                {shortcuts.map((section, sectionIndex) => (
                  <motion.div
                    key={section.category}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: sectionIndex * 0.1 }}
                  >
                    <h3 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wider">
                      {section.category}
                    </h3>
                    <div className="space-y-2">
                      {section.items.map((item, itemIndex) => (
                        <motion.div
                          key={itemIndex}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: sectionIndex * 0.1 + itemIndex * 0.05 }}
                          className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
                        >
                          <span className="text-sm text-gray-700">{item.description}</span>
                          <div className="flex items-center gap-1.5">
                            {item.keys.map((key, keyIndex) => (
                              <React.Fragment key={keyIndex}>
                                <kbd className="px-2.5 py-1.5 text-xs font-semibold text-gray-700 bg-gray-100 border border-gray-200 rounded-md shadow-sm">
                                  {getKeyDisplay(key)}
                                </kbd>
                                {keyIndex < item.keys.length - 1 && (
                                  <span className="text-gray-400 text-xs">+</span>
                                )}
                              </React.Fragment>
                            ))}
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            <div className="p-4 border-t bg-gray-50 text-center text-xs text-gray-500">
              提示：在 Mac 上，Ctrl 键对应 ⌘ 键
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
