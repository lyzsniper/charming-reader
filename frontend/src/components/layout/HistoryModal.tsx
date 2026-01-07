import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Search, MessageSquare, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface HistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HistoryModal: React.FC<HistoryModalProps> = ({ isOpen, onClose }) => {
  const historyItems = [
    { id: 1, title: "Transformer Architecture Analysis", date: "Today", preview: "The Transformer relies heavily on self-attention..." },
    { id: 2, title: "RAG Systems Survey", date: "Yesterday", preview: "Retrieval-Augmented Generation combines..." },
    { id: 3, title: "DeepSeek vs GPT-4", date: "Last Week", preview: "Comparing reasoning capabilities across models..." },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50"
          />
          <motion.div
            initial={{ opacity: 0, x: -300 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -300 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed left-0 top-0 bottom-0 w-80 bg-white shadow-2xl z-50 flex flex-col border-r"
          >
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="font-semibold text-lg">Chat History</h2>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="p-3">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" />
                <input 
                  className="w-full pl-9 pr-3 py-2 bg-gray-50 border rounded-lg text-sm outline-none focus:ring-1 focus:ring-black/10"
                  placeholder="Search chats..."
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {historyItems.map((item) => (
                <button 
                  key={item.id}
                  className="w-full text-left p-3 rounded-xl hover:bg-gray-100 transition-colors group"
                >
                  <div className="flex justify-between items-start mb-1">
                    <span className="font-medium text-sm text-gray-900 line-clamp-1">{item.title}</span>
                    <span className="text-[10px] text-gray-400 whitespace-nowrap ml-2">{item.date}</span>
                  </div>
                  <p className="text-xs text-gray-500 line-clamp-2 group-hover:text-gray-700">
                    {item.preview}
                  </p>
                </button>
              ))}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

