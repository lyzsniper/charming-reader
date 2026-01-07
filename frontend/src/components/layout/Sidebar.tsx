import React from 'react';
import { BookOpen, MessageSquare, Settings, History } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface SidebarProps {
  onOpenKnowledge: () => void;
  onOpenHistory: () => void;
  onOpenSettings: () => void;
  onGoHome: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  onOpenKnowledge, 
  onOpenHistory, 
  onOpenSettings,
  onGoHome 
}) => {
  return (
    <div className="h-screen w-16 border-r bg-gray-50/50 flex flex-col items-center py-4 gap-4 z-20">
      <div className="p-2 cursor-pointer hover:opacity-80 transition-opacity" onClick={onGoHome}>
        <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center text-white font-serif font-bold">
          P
        </div>
      </div>
      
      <div className="flex-1 flex flex-col gap-2 w-full px-2">
        <SidebarBtn icon={<MessageSquare className="w-5 h-5" />} label="Chat" active />
        <SidebarBtn icon={<History className="w-5 h-5" />} label="History" onClick={onOpenHistory} />
        <SidebarBtn icon={<BookOpen className="w-5 h-5" />} label="Knowledge" onClick={onOpenKnowledge} />
      </div>

      <div className="mb-4">
        <SidebarBtn icon={<Settings className="w-5 h-5" />} label="Settings" onClick={onOpenSettings} />
      </div>
    </div>
  );
};

interface SidebarBtnProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
}

const SidebarBtn: React.FC<SidebarBtnProps> = ({ icon, label, active, className, ...props }) => {
  return (
    <Button
      variant="ghost"
      size="icon"
      className={cn(
        "w-full aspect-square rounded-xl hover:bg-gray-200/50 transition-colors relative group",
        active && "bg-gray-200/50 text-black",
        !active && "text-gray-500",
        className
      )}
      {...props}
    >
      {icon}
      <span className="sr-only">{label}</span>
      
      {/* Tooltip-ish */}
      <div className="absolute left-full ml-2 px-2 py-1 bg-black text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
        {label}
      </div>
    </Button>
  );
};
