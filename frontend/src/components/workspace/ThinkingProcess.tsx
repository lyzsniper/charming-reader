import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight, Loader2, BrainCircuit } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ThinkingProcessProps {
  steps: string[];
  isThinking: boolean;
}

export const ThinkingProcess: React.FC<ThinkingProcessProps> = ({ steps, isThinking }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  if (steps.length === 0 && !isThinking) return null;

  return (
    <div className="mb-4 rounded-lg border bg-gray-50/50 overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 text-sm font-medium text-gray-600 hover:bg-gray-100/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {isThinking ? (
            <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
          ) : (
            <BrainCircuit className="w-4 h-4 text-green-600" />
          )}
          <span>{isThinking ? "Thinking..." : "Thought Process"}</span>
        </div>
        {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>

      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="px-3 pb-3 space-y-2">
              {steps.map((step, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-gray-500 font-mono">
                  <span className="mt-0.5 text-gray-300">›</span>
                  <span>{step}</span>
                </div>
              ))}
              {isThinking && (
                <div className="flex items-center gap-2 text-xs text-gray-400 font-mono pl-3 animate-pulse">
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />
                  Processing...
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

