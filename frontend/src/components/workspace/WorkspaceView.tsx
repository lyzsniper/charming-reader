import React, { useEffect, useState } from 'react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { Sidebar } from '../layout/Sidebar';
import { ChatPanel } from './ChatPanel';
import { ContextPanel } from './ContextPanel';
import { KnowledgeModal } from '../knowledge/KnowledgeModal';
import { History, X, Clock, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface WorkspaceViewProps {
  file: File | null;
  onGoHome: () => void;
}

export const WorkspaceView: React.FC<WorkspaceViewProps> = ({ file, onGoHome }) => {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [isKnowledgeOpen, setIsKnowledgeOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  useEffect(() => {
    if (file) {
      const url = URL.createObjectURL(file);
      setFileUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [file]);

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden relative">
      {/* Sidebar */}
      <Sidebar 
        onOpenKnowledge={() => setIsKnowledgeOpen(true)}
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onGoHome={onGoHome}
      />
      
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full">
        <PanelGroup direction="horizontal" className="flex-1">
          {/* Chat Panel - 40% default */}
          <Panel defaultSize={40} minSize={30} order={1} className="bg-white z-10">
            <ChatPanel />
          </Panel>
          
          <PanelResizeHandle className="w-1 bg-gray-100 hover:bg-blue-500 transition-colors cursor-col-resize z-20" />
          
          {/* Context Panel - 60% default */}
          <Panel defaultSize={60} minSize={30} order={2} className="bg-gray-50">
            <ContextPanel fileUrl={fileUrl} />
          </Panel>
        </PanelGroup>
      </div>

      {/* Modals */}
      <KnowledgeModal isOpen={isKnowledgeOpen} onClose={() => setIsKnowledgeOpen(false)} />
      
      {/* History Slide-over */}
      {isHistoryOpen && (
        <>
           <div className="fixed inset-0 bg-black/20 backdrop-blur-[1px] z-40" onClick={() => setIsHistoryOpen(false)} />
           <div className="fixed inset-y-0 left-16 z-50 w-80 bg-white border-r shadow-2xl animate-in slide-in-from-left duration-200">
             <div className="flex flex-col h-full">
               <div className="p-4 border-b flex items-center justify-between bg-gray-50/50">
                 <div className="flex items-center gap-2">
                   <History className="w-4 h-4 text-gray-500" />
                   <h2 className="font-semibold">History</h2>
                 </div>
                 <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setIsHistoryOpen(false)}>
                   <X className="w-4 h-4" />
                 </Button>
               </div>
               
               <div className="flex-1 overflow-y-auto p-2 space-y-2">
                 {[1, 2, 3].map((i) => (
                   <button key={i} className="w-full text-left p-3 rounded-lg hover:bg-gray-100 transition-colors group">
                     <div className="flex items-start gap-3">
                       <MessageSquare className="w-4 h-4 text-gray-400 mt-1" />
                       <div className="flex-1 min-w-0">
                         <div className="font-medium text-sm truncate">Research on Transformers</div>
                         <div className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                           <Clock className="w-3 h-3" />
                           2 hours ago
                         </div>
                       </div>
                     </div>
                   </button>
                 ))}
               </div>
             </div>
           </div>
        </>
      )}

      {/* Settings Modal - Simple Center Pop */}
      {isSettingsOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center" onClick={() => setIsSettingsOpen(false)}>
           <div className="w-[500px] bg-white rounded-2xl shadow-2xl p-6 animate-in zoom-in-95 duration-200" onClick={(e) => e.stopPropagation()}>
             <div className="flex justify-between items-center mb-6">
               <h2 className="text-xl font-bold">Settings</h2>
               <Button variant="ghost" size="icon" onClick={() => setIsSettingsOpen(false)}>
                 <X className="w-5 h-5" />
               </Button>
             </div>
             
             <div className="space-y-6">
               <div className="space-y-2">
                 <label className="text-sm font-medium">Model Configuration</label>
                 <select className="w-full p-2 border rounded-md bg-gray-50 text-sm">
                   <option>GPT-4o (Default)</option>
                   <option>Claude 3.5 Sonnet</option>
                   <option>Llama 3 70B</option>
                 </select>
               </div>
               
               <div className="space-y-2">
                 <label className="text-sm font-medium">RAG Sensitivity</label>
                 <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                   <div className="h-full w-2/3 bg-black" />
                 </div>
                 <div className="flex justify-between text-xs text-gray-400">
                    <span>Precise</span>
                    <span>Creative</span>
                 </div>
               </div>
             </div>
             
             <div className="mt-8 flex justify-end gap-2">
               <Button variant="outline" onClick={() => setIsSettingsOpen(false)}>Cancel</Button>
               <Button onClick={() => setIsSettingsOpen(false)}>Save Changes</Button>
             </div>
           </div>
        </div>
      )}
    </div>
  );
};
