import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, User, Monitor, Key, HelpCircle, LogOut, Sun, Moon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/hooks/useTheme';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const { theme, toggleTheme } = useTheme();
  
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed inset-0 m-auto w-full max-w-md h-fit bg-white rounded-2xl shadow-2xl z-50 overflow-hidden"
          >
            <div className="p-4 border-b flex items-center justify-between bg-gray-50/50">
              <h2 className="font-semibold text-lg">Settings</h2>
              <Button variant="ghost" size="icon" onClick={onClose}>
                <X className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="p-2">
              <div className="space-y-1">
                <SettingItem icon={<User />} label="Account" />
                <SettingItem 
                  icon={theme === 'dark' ? <Moon /> : <Sun />} 
                  label="Appearance" 
                  value={theme === 'dark' ? 'Dark' : 'Light'}
                  onClick={toggleTheme}
                />
                <SettingItem icon={<Key />} label="API Keys" />
                <SettingItem icon={<HelpCircle />} label="Help & Support" />
                <div className="my-2 border-t" />
                <SettingItem icon={<LogOut />} label="Log out" className="text-red-600 hover:bg-red-50 hover:text-red-700" />
              </div>
            </div>

            <div className="p-4 bg-gray-50 text-center text-xs text-gray-400">
              CharMing Reader v1.0.0
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

const SettingItem = ({ icon, label, value, className = "", onClick }: any) => (
  <button 
    onClick={onClick}
    className={`w-full flex items-center justify-between p-3 rounded-xl hover:bg-gray-100 transition-colors ${className}`}
  >
    <div className="flex items-center gap-3">
      <div className="w-5 h-5 opacity-70">{icon}</div>
      <span className="text-sm font-medium">{label}</span>
    </div>
    {value && <span className="text-xs text-gray-500">{value}</span>}
  </button>
);

