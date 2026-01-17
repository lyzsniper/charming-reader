import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Components } from 'react-markdown';
import { motion } from 'framer-motion';
import { Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { showSuccess } from '@/utils/dialogs';
import 'katex/dist/katex.min.css';

// 代码块组件（带复制功能）
const CodeBlock: React.FC<{ language: string; codeString: string }> = ({ language, codeString }) => {
  const [copied, setCopied] = useState(false);
  
  return (
    <div className="my-4 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 shadow-lg hover:shadow-xl transition-shadow group/codeblock">
      <div className="flex items-center justify-between px-4 py-2 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 border-b border-gray-200 dark:border-gray-700">
        <span className="text-xs font-mono font-semibold text-gray-700 dark:text-gray-300">{language}</span>
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-red-400"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-yellow-400"></div>
            <div className="w-2.5 h-2.5 rounded-full bg-green-400"></div>
          </div>
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(codeString);
                setCopied(true);
                showSuccess('代码已复制');
                setTimeout(() => setCopied(false), 2000);
              } catch (err) {
                console.error('复制失败', err);
              }
            }}
            className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors opacity-0 group-hover/codeblock:opacity-100"
            aria-label="复制代码"
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-green-600" />
            ) : (
              <Copy className="w-3.5 h-3.5 text-gray-600 dark:text-gray-400" />
            )}
          </motion.button>
        </div>
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={language}
        PreTag="div"
        className="!m-0 !rounded-none"
        customStyle={{
          margin: 0,
          padding: '1rem',
          background: '#282c34',
          fontSize: '0.875rem',
          lineHeight: '1.6',
        }}
      >
        {codeString}
      </SyntaxHighlighter>
    </div>
  );
};

// 图片组件（带懒加载）
const LazyImage: React.FC<{ src?: string; alt?: string }> = ({ src, alt }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  
  return (
    <div className="relative my-4">
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded-lg">
          <div className="w-8 h-8 border-2 border-gray-300 dark:border-gray-600 border-t-blue-500 rounded-full animate-spin" />
        </div>
      )}
      {hasError ? (
        <div className="flex items-center justify-center p-8 bg-gray-100 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <span className="text-sm text-gray-500 dark:text-gray-400">图片加载失败</span>
        </div>
      ) : (
        <img
          src={src}
          alt={alt}
          loading="lazy"
          onLoad={() => setIsLoading(false)}
          onError={() => {
            setIsLoading(false);
            setHasError(true);
          }}
          className={cn(
            "max-w-full h-auto rounded-lg shadow-md border border-gray-200 dark:border-gray-700 transition-opacity duration-300",
            isLoading ? "opacity-0" : "opacity-100"
          )}
        />
      )}
    </div>
  );
};

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
        remarkPlugins={[remarkGfm, remarkBreaks, remarkMath]}
        rehypePlugins={[rehypeKatex]}
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
                className="inline-flex items-center justify-center min-w-[1.2em] h-[1.2em] mx-0.5 text-[10px] font-bold text-blue-600 dark:text-blue-400 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-900/50 border border-blue-200 dark:border-blue-700 rounded shadow-sm hover:bg-blue-100 dark:hover:bg-blue-900/50 hover:scale-110 hover:shadow-md transition-all align-text-top cursor-pointer"
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
              return <CodeBlock language={match[1]} codeString={codeString} />;
            }
            
            return (
              <code
                className="px-1.5 py-0.5 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900 text-gray-800 dark:text-gray-200 rounded text-sm font-mono border border-gray-200 dark:border-gray-700 shadow-sm"
                {...props}
              >
                {children}
              </code>
            );
          },
          
          // 引用样式
          blockquote: ({ ...props }) => (
            <blockquote
              className="border-l-4 border-blue-500 dark:border-blue-400 pl-4 py-3 my-4 bg-gradient-to-r from-blue-50 to-blue-100/50 dark:from-blue-900/20 dark:to-blue-900/10 text-gray-700 dark:text-gray-300 italic rounded-r shadow-sm"
              {...props}
            />
          ),
          
          // 表格样式
          table: ({ ...props }) => (
            <div className="my-4 overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700 shadow-md hover:shadow-lg transition-shadow">
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
          
          // 图片样式 - 添加懒加载
          img: ({ src, alt, ...props }: any) => (
            <LazyImage src={src} alt={alt} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
