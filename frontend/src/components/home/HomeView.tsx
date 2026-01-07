import React, { useState, useRef } from 'react';
import { Paperclip, ArrowUp, FileText, Search, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface HomeViewProps {
  onStartChat: (message?: string, file?: File) => void;
}

export const HomeView: React.FC<HomeViewProps> = ({ onStartChat }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileUpload = (file: File) => {
    if (file.type === 'application/pdf') {
      onStartChat("", file);
    } else {
      alert("Only PDF files are supported for now.");
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (inputValue.trim()) {
      onStartChat(inputValue);
    }
  };

  const quickActions = [
    { icon: <FileText className="w-4 h-4" />, text: "Upload paper & summarize" },
    { icon: <Search className="w-4 h-4" />, text: "Search Transformer variants" },
    { icon: <Sparkles className="w-4 h-4" />, text: "Explain RAG concepts" },
  ];

  return (
    <div 
      className={cn(
        "min-h-screen flex flex-col items-center justify-center p-4 transition-colors duration-300 relative overflow-hidden",
        isDragging ? "bg-blue-50/50" : "bg-background"
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Background Decor */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-blue-100/30 blur-[120px]" />
        <div className="absolute bottom-[10%] right-[10%] w-[40%] h-[40%] rounded-full bg-purple-100/30 blur-[100px]" />
      </div>

      <div className="w-full max-w-2xl z-10 flex flex-col gap-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="w-16 h-16 bg-black text-white text-3xl font-serif font-bold rounded-2xl mx-auto flex items-center justify-center shadow-xl">
            P
          </div>
          <h1 className="text-4xl font-serif font-medium tracking-tight text-primary">
            PaperAgent
          </h1>
          <p className="text-muted-foreground text-lg font-light">
            Your streamlined academic workspace.
          </p>
        </div>

        {/* Omnibox */}
        <div className="relative group">
          <div className={cn(
            "absolute inset-0 bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-2xl blur-xl transition-opacity duration-500",
            isDragging || inputValue ? "opacity-100" : "opacity-0"
          )} />
          
          <div className="relative bg-white/80 backdrop-blur-xl border border-white/20 shadow-2xl rounded-2xl p-2 transition-all duration-300 hover:shadow-blue-900/5 ring-1 ring-black/5">
            <form onSubmit={handleSubmit} className="flex flex-col gap-2">
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
                placeholder="Ask anything or drag a PDF here..."
                className="w-full bg-transparent border-none text-lg px-4 py-3 placeholder:text-gray-400 focus:ring-0 resize-none min-h-[60px] max-h-[200px]"
                rows={1}
              />
              
              <div className="flex justify-between items-center px-2 pb-1">
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="ghost" 
                    size="icon"
                    className="text-gray-400 hover:text-gray-600 hover:bg-gray-100/50 rounded-xl"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Paperclip className="w-5 h-5" />
                  </Button>
                  <input
                    type="file"
                    ref={fileInputRef}
                    className="hidden"
                    accept=".pdf"
                    onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
                  />
                </div>
                
                <Button 
                  type="submit" 
                  size="icon"
                  className={cn(
                    "rounded-xl transition-all duration-300",
                    inputValue ? "bg-black text-white hover:bg-gray-800" : "bg-gray-100 text-gray-400 hover:bg-gray-200"
                  )}
                  disabled={!inputValue.trim()}
                >
                  <ArrowUp className="w-5 h-5" />
                </Button>
              </div>
            </form>
          </div>
        </div>

        {/* Pills */}
        <div className="flex flex-wrap justify-center gap-3">
          {quickActions.map((action, i) => (
            <button
              key={i}
              onClick={() => onStartChat(action.text)}
              className="flex items-center gap-2 px-4 py-2 bg-white/50 hover:bg-white/80 backdrop-blur-sm border border-black/5 rounded-full text-sm text-gray-600 hover:text-black transition-all shadow-sm hover:shadow-md hover:-translate-y-0.5"
            >
              {action.icon}
              {action.text}
            </button>
          ))}
        </div>
      </div>
      
      {/* Footer Hint */}
      {isDragging && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-blue-50/90 backdrop-blur-sm border-2 border-dashed border-blue-400 m-4 rounded-3xl animate-pulse">
          <div className="text-2xl font-medium text-blue-600">
            Drop PDF to analyze
          </div>
        </div>
      )}
    </div>
  );
};
