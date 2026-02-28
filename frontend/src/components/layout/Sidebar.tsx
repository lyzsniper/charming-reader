import React, { useRef, useCallback } from 'react';
import { BookOpen, MessageSquare, Settings, History, Brain, Sparkles, Sliders } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface SidebarProps {
  onOpenKnowledge: () => void;
  onOpenHistory: () => void;
  onOpenSettings: () => void;
  onOpenModels?: () => void;
  onOpenSkillsMarket?: () => void;
  onOpenConfigPanel?: () => void;
  onGoHome: () => void;
  isKnowledgeOpen?: boolean;
  isHistoryOpen?: boolean;
  isSettingsOpen?: boolean;
  isModelsOpen?: boolean;
  isSkillsMarketOpen?: boolean;
  isConfigPanelOpen?: boolean;
  viewMode?: 'home' | 'workspace' | 'skills-market' | 'config-panel';
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  onOpenKnowledge, 
  onOpenHistory, 
  onOpenSettings,
  onOpenModels,
  onOpenSkillsMarket,
  onOpenConfigPanel,
  onGoHome,
  isKnowledgeOpen = false,
  isHistoryOpen = false,
  isSettingsOpen = false,
  isModelsOpen = false,
  isSkillsMarketOpen = false,
  isConfigPanelOpen = false,
  viewMode = 'home',
}) => {
  // 使用 ref 来跟踪上次点击时间，实现简单的防抖
  const lastClickTimeRef = useRef<Record<string, number>>({});
  
  // 防抖点击处理函数
  const createDebouncedHandler = useCallback((key: string, handler: () => void, delay: number = 300) => {
    return () => {
      const now = Date.now();
      const lastClick = lastClickTimeRef.current[key] || 0;
      
      if (now - lastClick < delay) {
        // 如果距离上次点击时间太短，忽略此次点击
        return;
      }
      
      lastClickTimeRef.current[key] = now;
      handler();
    };
  }, []);

  const handleKnowledgeClick = createDebouncedHandler('knowledge', onOpenKnowledge);
  const handleHistoryClick = createDebouncedHandler('history', onOpenHistory);
  const handleSettingsClick = createDebouncedHandler('settings', onOpenSettings);
  const handleModelsClick = createDebouncedHandler('models', onOpenModels || (() => {}));
  const handleSkillsMarketClick = createDebouncedHandler('skills-market', onOpenSkillsMarket || (() => {}));
  const handleConfigPanelClick = createDebouncedHandler('config-panel', onOpenConfigPanel || (() => {}));
  const handleGoHomeClick = createDebouncedHandler('home', onGoHome);

  // Chat 按钮在 workspace 模式下激活
  const isChatActive = viewMode === 'workspace' && !isKnowledgeOpen;

  return (
    <motion.div
      initial={{ x: -64, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="h-screen w-16 md:w-16 sm:w-14 border-r bg-gradient-to-b from-gray-50/80 to-gray-50/50 backdrop-blur-sm flex flex-col items-center py-4 gap-4 z-20 shadow-sm"
    >
      <motion.div 
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
        className="p-2 cursor-pointer transition-opacity" 
        onClick={handleGoHomeClick}
      >
        <motion.div
          whileHover={{ rotate: [0, -5, 5, -5, 0] }}
          transition={{ duration: 0.5 }}
          className="w-8 h-8 bg-gradient-to-br from-black to-gray-800 rounded-lg flex items-center justify-center text-white font-serif font-bold shadow-md ring-1 ring-gray-200/50"
        >
          P
        </motion.div>
      </motion.div>
      
      <div className="flex-1 flex flex-col gap-2 w-full px-2">
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
        <SidebarBtn 
          icon={<MessageSquare className="w-5 h-5" />} 
          label="Chat" 
          active={isChatActive}
          onClick={handleGoHomeClick}
        />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15 }}
        >
        <SidebarBtn 
          icon={<History className="w-5 h-5" />} 
          label="History" 
          active={isHistoryOpen}
          onClick={handleHistoryClick} 
        />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
        >
        <SidebarBtn 
          icon={<BookOpen className="w-5 h-5" />} 
          label="Knowledge" 
          active={isKnowledgeOpen}
          onClick={handleKnowledgeClick} 
        />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.25 }}
        >
        <SidebarBtn 
          icon={<Brain className="w-5 h-5" />} 
          label="Models" 
          active={isModelsOpen}
          onClick={handleModelsClick} 
        />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
        >
        <SidebarBtn 
          icon={<Sparkles className="w-5 h-5" />} 
          label="Skills Market" 
          active={isSkillsMarketOpen}
          onClick={handleSkillsMarketClick} 
        />
        </motion.div>
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.35 }}
        >
        <SidebarBtn 
          icon={<Sliders className="w-5 h-5" />} 
          label="Config Panel" 
          active={isConfigPanelOpen}
          onClick={handleConfigPanelClick} 
        />
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="mb-4"
      >
        <SidebarBtn 
          icon={<Settings className="w-5 h-5" />} 
          label="Settings" 
          active={isSettingsOpen}
          onClick={handleSettingsClick} 
        />
      </motion.div>
    </motion.div>
  );
};

interface SidebarBtnProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
}

const SidebarBtn: React.FC<SidebarBtnProps> = ({ icon, label, active, className, ...props }) => {
  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className="relative"
    >
    <Button
      variant="ghost"
      size="icon"
        aria-label={label}
        aria-pressed={active}
      className={cn(
          "w-full aspect-square rounded-xl transition-all duration-200 relative group ripple",
          active 
            ? "bg-gradient-to-br from-gray-200/80 to-gray-200/50 text-black shadow-md" 
            : "text-gray-500 hover:bg-gray-200/30 hover:text-gray-700",
        className
      )}
      {...props}
      >
        <motion.div
          animate={active ? { scale: 1.1 } : { scale: 1 }}
          transition={{ duration: 0.2 }}
    >
      {icon}
        </motion.div>
      <span className="sr-only">{label}</span>
      
        {/* Enhanced Tooltip */}
        <motion.div
          initial={{ opacity: 0, x: -5 }}
          whileHover={{ opacity: 1, x: 0 }}
          className="absolute left-full ml-3 px-3 py-1.5 bg-gray-900 text-white text-xs rounded-lg shadow-lg pointer-events-none whitespace-nowrap z-50"
        >
        {label}
          <div className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1 w-2 h-2 bg-gray-900 rotate-45" />
        </motion.div>
        
        {/* Active indicator */}
        {active && (
          <motion.div
            layoutId="activeIndicator"
            className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-black rounded-r-full"
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
          />
        )}
    </Button>
    </motion.div>
  );
};
