import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, FileText, Upload, Search, Database } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface KnowledgeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const KnowledgeModal: React.FC<KnowledgeModalProps> = ({ isOpen, onClose }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
          />
          
          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-4 md:inset-10 bg-white rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-black text-white rounded-xl flex items-center justify-center">
                  <Database className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-xl font-bold font-serif">Knowledge Base</h2>
                  <p className="text-sm text-gray-500">Manage your research assets and vectorized chunks</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full hover:bg-gray-100">
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* Content - Two columns */}
            <div className="flex-1 flex overflow-hidden">
              
              {/* Sidebar List */}
              <div className="w-64 bg-gray-50 border-r p-4 flex flex-col gap-2">
                 <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Datasets</div>
                 <Button variant="secondary" className="justify-start bg-white shadow-sm text-black">
                    <FileText className="w-4 h-4 mr-2" />
                    Attention Is All You Need
                 </Button>
                 <Button variant="ghost" className="justify-start text-gray-600 hover:bg-gray-200/50">
                    <FileText className="w-4 h-4 mr-2" />
                    BERT Pre-training
                 </Button>
                 <Button variant="ghost" className="justify-start text-gray-600 hover:bg-gray-200/50">
                    <FileText className="w-4 h-4 mr-2" />
                    RAG Survey 2024
                 </Button>

                 <div className="mt-auto pt-4 border-t border-gray-200">
                   <div className="border-2 border-dashed border-gray-300 rounded-xl p-4 flex flex-col items-center justify-center text-gray-400 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-500 transition-colors cursor-pointer group">
                     <Upload className="w-6 h-6 mb-2 group-hover:scale-110 transition-transform" />
                     <span className="text-xs font-medium">Drag PDF here</span>
                   </div>
                 </div>
              </div>

              {/* Main Detail Area - The "Chunk Microscope" */}
              <div className="flex-1 flex flex-col bg-white">
                {/* Search / Filter Bar */}
                <div className="p-4 border-b flex items-center gap-3">
                  <Search className="w-5 h-5 text-gray-400" />
                  <input 
                    className="flex-1 text-sm outline-none placeholder:text-gray-400" 
                    placeholder="Search for chunks or test recall..."
                  />
                </div>

                {/* Chunks Visualization */}
                <div className="flex-1 p-6 overflow-y-auto bg-gray-50/30">
                  <div className="grid grid-cols-1 gap-4 max-w-3xl mx-auto">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <div key={i} className="bg-white border rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow group relative">
                         <div className="flex items-center justify-between mb-2">
                           <div className="flex items-center gap-2">
                             <span className="bg-blue-100 text-blue-700 text-[10px] font-mono px-1.5 py-0.5 rounded">ID: {1000 + i}</span>
                             <span className="text-xs text-gray-400">Tokens: 128</span>
                           </div>
                           <span className="text-xs font-medium text-green-600 opacity-0 group-hover:opacity-100 transition-opacity">
                             Sim: 0.92
                           </span>
                         </div>
                         <p className="text-sm text-gray-700 leading-relaxed font-serif">
                           The Transformer follows this overall architecture using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder, shown in the left and right halves of Figure 1, respectively.
                         </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};


