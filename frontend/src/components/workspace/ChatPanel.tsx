import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Paperclip, StopCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { ThinkingProcess } from './ThinkingProcess';

// Mock types for now
interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  thinking?: string[]; // Steps for the thinking process
  citations?: string[]; // IDs or links
}

// Custom hook to emit citation clicks (simple event bus or prop drill would work, 
// using CustomEvent for decoupling in this quick refactor)
export const CITATION_EVENT = 'citation-click';

export const ChatPanel: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'agent',
      content: "Hello! I'm PaperAgent. Upload a PDF or ask me a research question to get started.",
      thinking: [],
    }
  ]);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isThinking]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input
    };

    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsThinking(true);

    // Simulate thinking process
    const thinkingId = Date.now() + 1;
    setMessages(prev => [...prev, {
      id: thinkingId.toString(),
      role: 'agent',
      content: "",
      thinking: ["Parsing query...", "Retrieving relevant contexts...", "Synthesizing answer..."]
    }]);

    // Simulate API delay
    setTimeout(() => {
      setMessages(prev => prev.map(m => 
        m.id === thinkingId.toString() 
          ? { 
              ...m, 
              content: "Based on the analysis of the provided documents, the Transformer architecture introduced by Vaswani et al. relies entirely on **self-attention mechanisms** to compute representations of its input and output without using sequence-aligned RNNs or convolution. \n\n Key advantages include:\n1. **Parallelization**: Significant reduction in training time [1].\n2. **Long-range Dependencies**: Better at capturing relationships between distant words [2].",
              thinking: ["Parsing query...", "Retrieving relevant contexts...", "Synthesizing answer...", "Formatting citations..."]
            } 
          : m
      ));
      setIsThinking(false);
    }, 2000);
  };

  // Custom renderer for citations
  const CitationRenderer = (props: any) => {
    // Basic regex to find [1], [2] etc. in text nodes is hard with just components.
    // react-markdown passes text. We can't easily intercept text content inside p tags 
    // without a plugin like remark-directive or custom regex parsing.
    // FOR SIMPLICITY: We will assume the agent returns standard markdown links for citations
    // e.g. "training time [[1]](#citation-1)." OR we just use a regex replacer on the content string before rendering.
    return <span>{props.children}</span>;
  }
  
  // A helper to preprocess content to make [1] clickable links or custom components
  const preprocessContent = (content: string) => {
    // This is a naive replacement to turn [1] into a custom link we can catch
    // In a real app, use a remark plugin.
    return content.replace(/\[(\d+)\]/g, '[`[$1]`](#citation-$1)');
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Messages Area */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth"
      >
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={cn(
              "flex flex-col max-w-[90%]",
              msg.role === 'user' ? "self-end items-end" : "self-start items-start"
            )}
          >
            {msg.role === 'agent' && (
               <div className="w-8 h-8 mb-2 bg-black text-white rounded-lg flex items-center justify-center font-serif text-xs font-bold shadow-sm">
                 AI
               </div>
            )}
            
            <div className={cn(
              "rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
              msg.role === 'user' 
                ? "bg-blue-600 text-white rounded-tr-sm" 
                : "bg-white border border-gray-100 text-gray-800 rounded-tl-sm w-full"
            )}>
              {msg.thinking && (
                <ThinkingProcess steps={msg.thinking} isThinking={isThinking && msg.content === ""} />
              )}
              
              {msg.content && (
                <div className="prose prose-sm max-w-none prose-p:my-1 prose-headings:my-2">
                  <ReactMarkdown 
                    components={{
                      a: ({node, ...props}) => {
                         // Check if it's our citation link
                         if (props.href?.startsWith('#citation-')) {
                           const id = props.href.split('-')[1];
                           return (
                             <button 
                               className="inline-flex items-center justify-center min-w-[1.2em] h-[1.2em] mx-0.5 text-[10px] font-bold text-blue-600 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 hover:scale-110 transition-all align-text-top cursor-pointer"
                               onClick={(e) => {
                                 e.preventDefault();
                                 window.dispatchEvent(new CustomEvent(CITATION_EVENT, { detail: { id } }));
                               }}
                             >
                               {id}
                             </button>
                           );
                         }
                         return <a {...props} className="text-blue-600 hover:underline" />;
                      }
                    }}
                  >
                    {preprocessContent(msg.content)}
                  </ReactMarkdown>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white/80 backdrop-blur-md border-t border-gray-100">
        <div className="relative flex items-end gap-2 p-2 bg-gray-50 border rounded-xl focus-within:ring-1 focus-within:ring-black/10 transition-all">
          <Button variant="ghost" size="icon" className="text-gray-400 hover:text-gray-600 h-10 w-10 shrink-0">
            <Paperclip className="w-5 h-5" />
          </Button>
          
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask a follow-up question..."
            className="flex-1 bg-transparent border-none resize-none focus:ring-0 max-h-32 min-h-[40px] py-2 text-sm outline-none"
            rows={1}
          />
          
          <Button 
            onClick={handleSend}
            disabled={!input.trim() || isThinking}
            size="icon"
            className={cn(
              "h-10 w-10 shrink-0 transition-all",
              input.trim() ? "bg-black text-white" : "bg-gray-200 text-gray-400"
            )}
          >
            {isThinking ? <StopCircle className="w-5 h-5" /> : <Send className="w-5 h-5" />}
          </Button>
        </div>
        <div className="text-center mt-2 text-xs text-gray-400">
          AI can make mistakes. Please verify important information.
        </div>
      </div>
    </div>
  );
};
