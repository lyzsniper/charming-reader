import React, { useState, useEffect } from 'react';
import { FileText, List, Search, ZoomIn, ZoomOut, RotateCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Document, Page, pdfjs } from 'react-pdf';
import { CITATION_EVENT } from './ChatPanel';

// Setup pdf worker
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface ContextPanelProps {
  fileUrl?: string | null;
}

export const ContextPanel: React.FC<ContextPanelProps> = ({ fileUrl }) => {
  const [activeTab, setActiveTab] = useState<'pdf' | 'chunks'>('pdf');
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState(1.0);
  const [rotation, setRotation] = useState(0);

  // Listen for citation clicks
  useEffect(() => {
    const handleCitationClick = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      console.log("Jump to citation:", detail.id);
      // Mock logic: Jump to page based on ID (randomly for demo)
      // In real app, you'd map Citation ID -> Page Number
      const targetPage = (parseInt(detail.id) % (numPages || 1)) + 1;
      setPageNumber(targetPage);
      setActiveTab('pdf');
    };

    window.addEventListener(CITATION_EVENT, handleCitationClick);
    return () => window.removeEventListener(CITATION_EVENT, handleCitationClick);
  }, [numPages]);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
  }

  return (
    <div className="h-full flex flex-col bg-gray-50 border-l border-gray-200">
      {/* Header Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b h-14">
        <div className="flex items-center gap-2 overflow-hidden">
          <span className="font-semibold text-sm text-gray-700 truncate max-w-[150px]">
            {fileUrl ? "Document.pdf" : "No Document"}
          </span>
          {fileUrl && numPages && (
            <span className="text-xs text-gray-400">
              ({pageNumber} / {numPages})
            </span>
          )}
        </div>
        
        {/* View Controls */}
        {activeTab === 'pdf' && fileUrl && (
          <div className="flex items-center gap-1 mr-2">
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setScale(s => Math.max(0.5, s - 0.1))}>
              <ZoomOut className="w-4 h-4" />
            </Button>
            <span className="text-xs w-10 text-center">{Math.round(scale * 100)}%</span>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setScale(s => Math.min(2.0, s + 0.1))}>
              <ZoomIn className="w-4 h-4" />
            </Button>
          </div>
        )}

        <div className="flex bg-gray-100 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('pdf')}
            className={cn(
              "px-3 py-1 rounded-md text-xs font-medium transition-all",
              activeTab === 'pdf' ? "bg-white shadow-sm text-black" : "text-gray-500 hover:text-gray-700"
            )}
          >
            PDF View
          </button>
          <button
            onClick={() => setActiveTab('chunks')}
            className={cn(
              "px-3 py-1 rounded-md text-xs font-medium transition-all",
              activeTab === 'chunks' ? "bg-white shadow-sm text-black" : "text-gray-500 hover:text-gray-700"
            )}
          >
            Chunks
          </button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-hidden relative bg-gray-100/50">
        {activeTab === 'pdf' ? (
          fileUrl ? (
            <div className="h-full overflow-auto flex justify-center p-4">
              <Document
                file={fileUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                className="shadow-lg"
              >
                <Page 
                  pageNumber={pageNumber} 
                  scale={scale} 
                  renderAnnotationLayer={false}
                  renderTextLayer={false}
                  className="border border-gray-200"
                />
              </Document>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-4">
              <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center">
                <FileText className="w-8 h-8 text-gray-400" />
              </div>
              <p>Upload a PDF to view it here</p>
            </div>
          )
        ) : (
          <div className="p-4 space-y-4 overflow-y-auto h-full">
             <div className="flex items-center gap-2 mb-4 bg-white p-2 rounded-lg border sticky top-0 shadow-sm z-10">
               <Search className="w-4 h-4 text-gray-400" />
               <input 
                 className="flex-1 text-sm outline-none" 
                 placeholder="Search in document..."
               />
             </div>
             
             {/* Mock Chunks */}
             {[1, 2, 3].map((i) => (
               <div key={i} className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm hover:border-blue-300 transition-colors cursor-pointer group">
                 <div className="flex justify-between items-start mb-2">
                   <span className="text-xs font-mono bg-gray-100 px-2 py-0.5 rounded text-gray-500">Chunk #{i}</span>
                   <span className="text-xs text-gray-400">Score: 0.9{8-i}</span>
                 </div>
                 <p className="text-sm text-gray-600 leading-relaxed group-hover:text-gray-900 font-serif">
                   The Transformer model architecture eschews recurrence and instead relies entirely on an attention mechanism to draw global dependencies between input and output. The Transformer allows for significantly more parallelization...
                 </p>
               </div>
             ))}
          </div>
        )}
      </div>
    </div>
  );
};
