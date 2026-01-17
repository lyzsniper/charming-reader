import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight, Loader2, BrainCircuit, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ThinkingProcessProps {
  steps: string[];
  isThinking: boolean;
}

export const ThinkingProcess: React.FC<ThinkingProcessProps> = ({ steps, isThinking }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  if (steps.length === 0 && !isThinking) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-4 rounded-xl border border-gray-200/80 bg-gradient-to-br from-gray-50/80 via-blue-50/30 to-purple-50/20 overflow-hidden shadow-md hover:shadow-lg transition-shadow"
    >
      <motion.button
        whileHover={{ backgroundColor: 'rgba(0, 0, 0, 0.02)' }}
        whileTap={{ scale: 0.98 }}
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3.5 text-sm font-medium text-gray-700 hover:text-gray-900 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          {isThinking ? (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <Loader2 className="w-4 h-4 text-blue-500" />
            </motion.div>
          ) : (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 200, damping: 15 }}
            >
              <BrainCircuit className="w-4 h-4 text-green-600" />
            </motion.div>
          )}
          <span className="font-semibold">{isThinking ? "Thinking..." : "Thought Process"}</span>
          {steps.length > 0 && (
            <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full font-medium">
              {steps.length}
            </span>
          )}
        </div>
        <motion.div
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="w-4 h-4 text-gray-400" />
        </motion.div>
      </motion.button>

      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-3.5 pb-3.5 space-y-2.5 bg-white/30 backdrop-blur-sm">
              {steps.map((step, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-start gap-2.5 text-xs text-gray-600 group"
                >
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: i * 0.05 + 0.1, type: "spring" }}
                    className="mt-0.5 flex-shrink-0"
                  >
                    {isThinking && i === steps.length - 1 ? (
                      <motion.div
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                        className="w-1.5 h-1.5 rounded-full bg-blue-500"
                      />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                    )}
                  </motion.div>
                  <span className="flex-1 leading-relaxed font-mono group-hover:text-gray-800 transition-colors">
                    {step}
                  </span>
                </motion.div>
              ))}
              {isThinking && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex items-center gap-2 text-xs text-gray-400 font-mono pl-5"
                >
                  <motion.span
                    animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    className="w-1.5 h-1.5 rounded-full bg-blue-400"
                  />
                  <span>Processing...</span>
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

