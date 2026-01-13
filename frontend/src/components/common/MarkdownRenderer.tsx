import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Components } from 'react-markdown';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  onCitationClick?: (id: string) => void;
  citationEventName?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className,
  onCitationClick,
  citationEventName,
}) => {
  return (
    <div className={cn("markdown-content", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          // 标题样式
          h1: ({ ...props }) => (
            <h1 className="text-2xl font-bold mt-6 mb-4 text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-2" {...props} />
          ),
          h2: ({ ...props }) => (
            <h2 className="text-xl font-bold mt-5 mb-3 text-gray-900 dark:text-gray-100 border-b border-gray-200 dark:border-gray-700 pb-1.5" {...props} />
          ),
          h3: ({ ...props }) => (
            <h3 className="text-lg font-semibold mt-4 mb-2 text-gray-900 dark:text-gray-100" {...props} />
          ),
          h4: ({ ...props }) => (
            <h4 className="text-base font-semibold mt-3 mb-2 text-gray-900 dark:text-gray-100" {...props} />
          ),
          h5: ({ ...props }) => (
            <h5 className="text-sm font-semibold mt-2 mb-1 text-gray-800 dark:text-gray-200" {...props} />
          ),
          h6: ({ ...props }) => (
            <h6 className="text-xs font-semibold mt-2 mb-1 text-gray-700 dark:text-gray-300" {...props} />
          ),
          
          // 段落样式
          p: ({ ...props }) => (
            <p className="mb-3 leading-7 text-gray-800 dark:text-gray-200" {...props} />
          ),
          
          // 列表样式
          ul: ({ ...props }) => (
            <ul className="mb-3 ml-6 list-disc space-y-1 text-gray-800 dark:text-gray-200" {...props} />
          ),
          ol: ({ ...props }) => (
            <ol className="mb-3 ml-6 list-decimal space-y-1 text-gray-800 dark:text-gray-200" {...props} />
          ),
          li: ({ ...props }) => (
            <li className="leading-7" {...props} />
          ),
          
          // 链接样式
          a: ({ href, ...props }: any) => {
            // 处理引用链接
            if (href?.startsWith('#citation-')) {
              const id = href.split('-')[1];
              return (
                <button
                  className="inline-flex items-center justify-center min-w-[1.2em] h-[1.2em] mx-0.5 text-[10px] font-bold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded hover:bg-blue-100 dark:hover:bg-blue-900/50 hover:scale-110 transition-all align-text-top cursor-pointer"
                  onClick={(e) => {
                    e.preventDefault();
                    if (onCitationClick) {
                      onCitationClick(id);
                    } else if (citationEventName) {
                      window.dispatchEvent(new CustomEvent(citationEventName, { detail: { id } }));
                    }
                  }}
                >
                  {id}
                </button>
              );
            }
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline font-medium transition-colors"
                {...props}
              />
            );
          },
          
          // 代码块样式
          code: ({ inline, className, children, ...props }: any) => {
            const match = /language-(\w+)/.exec(className || '');
            const codeString = String(children).replace(/\n$/, '');
            
            if (!inline && match) {
              return (
                <div className="my-4 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 shadow-sm">
                  <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                    <span className="text-xs font-mono text-gray-600 dark:text-gray-400">{match[1]}</span>
                  </div>
                  <SyntaxHighlighter
                    style={oneDark}
                    language={match[1]}
                    PreTag="div"
                    className="!m-0 !rounded-none"
                    customStyle={{
                      margin: 0,
                      padding: '1rem',
                      background: '#282c34',
                      fontSize: '0.875rem',
                      lineHeight: '1.5',
                    }}
                    {...props}
                  >
                    {codeString}
                  </SyntaxHighlighter>
                </div>
              );
            }
            
            return (
              <code
                className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded text-sm font-mono border border-gray-200 dark:border-gray-700"
                {...props}
              >
                {children}
              </code>
            );
          },
          
          // 引用样式
          blockquote: ({ ...props }) => (
            <blockquote
              className="border-l-4 border-blue-500 dark:border-blue-400 pl-4 py-2 my-4 bg-blue-50 dark:bg-blue-900/20 text-gray-700 dark:text-gray-300 italic rounded-r"
              {...props}
            />
          ),
          
          // 表格样式
          table: ({ ...props }) => (
            <div className="my-4 overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700" {...props} />
            </div>
          ),
          thead: ({ ...props }) => (
            <thead className="bg-gray-50 dark:bg-gray-800" {...props} />
          ),
          tbody: ({ ...props }) => (
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700" {...props} />
          ),
          tr: ({ ...props }) => (
            <tr className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors" {...props} />
          ),
          th: ({ ...props }) => (
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider" {...props} />
          ),
          td: ({ ...props }) => (
            <td className="px-4 py-3 text-sm text-gray-800 dark:text-gray-200" {...props} />
          ),
          
          // 水平线样式
          hr: ({ ...props }) => (
            <hr className="my-6 border-0 border-t border-gray-300 dark:border-gray-600" {...props} />
          ),
          
          // 强调样式
          strong: ({ ...props }) => (
            <strong className="font-bold text-gray-900 dark:text-gray-100" {...props} />
          ),
          em: ({ ...props }) => (
            <em className="italic text-gray-800 dark:text-gray-200" {...props} />
          ),
          
          // 图片样式
          img: ({ ...props }) => (
            <img
              className="max-w-full h-auto rounded-lg my-4 shadow-md border border-gray-200 dark:border-gray-700"
              {...props}
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
