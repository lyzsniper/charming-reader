import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, User, Monitor, Key, HelpCircle, LogOut, Sun, Moon, Bell, Globe, Shield, Database, Zap, Info, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/hooks/useTheme';
import { cn } from '@/lib/utils';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type SettingsSection = 'general' | 'account' | 'privacy' | 'advanced';

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const { theme, toggleTheme } = useTheme();
  const [activeSection, setActiveSection] = useState<SettingsSection>('general');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [autoSaveEnabled, setAutoSaveEnabled] = useState(true);
  
  const sections: Array<{ id: SettingsSection; label: string; icon: React.ReactNode }> = [
    { id: 'general', label: '通用设置', icon: <Monitor className="w-4 h-4" /> },
    { id: 'account', label: '账户', icon: <User className="w-4 h-4" /> },
    { id: 'privacy', label: '隐私与安全', icon: <Shield className="w-4 h-4" /> },
    { id: 'advanced', label: '高级', icon: <Zap className="w-4 h-4" /> },
  ];
  
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
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed inset-0 m-auto w-full max-w-4xl h-[85vh] max-h-[800px] bg-white rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col"
          >
            {/* Header */}
            <div className="p-6 border-b flex items-center justify-between bg-gradient-to-r from-gray-50 to-white">
              <div>
                <h2 className="font-semibold text-xl text-gray-900">设置</h2>
                <p className="text-sm text-gray-500 mt-1">管理您的应用偏好和账户设置</p>
              </div>
              <Button variant="ghost" size="icon" onClick={onClose} className="rounded-xl">
                <X className="w-5 h-5" />
              </Button>
            </div>
            
            <div className="flex flex-1 overflow-hidden">
              {/* Sidebar Navigation */}
              <div className="w-64 border-r bg-gray-50/50 p-4 overflow-y-auto">
                <div className="space-y-1">
                  {sections.map((section) => (
                    <motion.button
                      key={section.id}
                      whileHover={{ x: 2 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => setActiveSection(section.id)}
                      className={cn(
                        "w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all",
                        activeSection === section.id
                          ? "bg-blue-50 text-blue-700 shadow-sm"
                          : "text-gray-600 hover:bg-gray-100"
                      )}
                    >
                      <div className={cn("opacity-70", activeSection === section.id && "opacity-100")}>
                        {section.icon}
                      </div>
                      <span>{section.label}</span>
                    </motion.button>
                  ))}
                </div>
              </div>
              
              {/* Content Area */}
              <div className="flex-1 overflow-y-auto p-6">
                <AnimatePresence mode="wait">
                  {activeSection === 'general' && (
                    <motion.div
                      key="general"
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      className="space-y-6"
                    >
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">外观</h3>
                        <SettingCard
                          icon={<Sun className="w-5 h-5" />}
                          title="主题模式"
                          description={theme === 'dark' ? '当前使用深色模式' : '当前使用浅色模式'}
                          action={
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={toggleTheme}
                              className="rounded-lg"
                            >
                              {theme === 'dark' ? <Moon className="w-4 h-4 mr-2" /> : <Sun className="w-4 h-4 mr-2" />}
                              切换到{theme === 'dark' ? '浅色' : '深色'}模式
                            </Button>
                          }
                        />
                      </div>
                      
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">通知</h3>
                        <SettingCard
                          icon={<Bell className="w-5 h-5" />}
                          title="启用通知"
                          description="接收重要更新和消息提醒"
                          action={
                            <label className="relative inline-flex items-center cursor-pointer">
                              <input
                                type="checkbox"
                                checked={notificationsEnabled}
                                onChange={(e) => setNotificationsEnabled(e.target.checked)}
                                className="sr-only peer"
                              />
                              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                            </label>
                          }
                        />
                      </div>
                      
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">数据</h3>
                        <SettingCard
                          icon={<Database className="w-5 h-5" />}
                          title="自动保存"
                          description="自动保存对话历史和设置"
                          action={
                            <label className="relative inline-flex items-center cursor-pointer">
                              <input
                                type="checkbox"
                                checked={autoSaveEnabled}
                                onChange={(e) => setAutoSaveEnabled(e.target.checked)}
                                className="sr-only peer"
                              />
                              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                            </label>
                          }
                        />
                      </div>
                    </motion.div>
                  )}
                  
                  {activeSection === 'account' && (
                    <motion.div
                      key="account"
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      className="space-y-6"
                    >
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">账户信息</h3>
                        <SettingCard
                          icon={<User className="w-5 h-5" />}
                          title="用户资料"
                          description="查看和编辑您的个人信息"
                          action={
                            <Button variant="ghost" size="sm" className="rounded-lg">
                              编辑
                              <ChevronRight className="w-4 h-4 ml-1" />
                            </Button>
                          }
                        />
                      </div>
                      
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">API 配置</h3>
                        <SettingCard
                          icon={<Key className="w-5 h-5" />}
                          title="API 密钥"
                          description="管理您的 API 密钥和访问权限"
                          action={
                            <Button variant="ghost" size="sm" className="rounded-lg">
                              管理
                              <ChevronRight className="w-4 h-4 ml-1" />
                            </Button>
                          }
                        />
                      </div>
                    </motion.div>
                  )}
                  
                  {activeSection === 'privacy' && (
                    <motion.div
                      key="privacy"
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      className="space-y-6"
                    >
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">隐私设置</h3>
                        <SettingCard
                          icon={<Shield className="w-5 h-5" />}
                          title="数据隐私"
                          description="控制您的数据如何被使用和存储"
                          action={
                            <Button variant="ghost" size="sm" className="rounded-lg">
                              查看详情
                              <ChevronRight className="w-4 h-4 ml-1" />
                            </Button>
                          }
                        />
                      </div>
                    </motion.div>
                  )}
                  
                  {activeSection === 'advanced' && (
                    <motion.div
                      key="advanced"
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -10 }}
                      className="space-y-6"
                    >
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">高级选项</h3>
                        <SettingCard
                          icon={<Zap className="w-5 h-5" />}
                          title="性能优化"
                          description="调整应用性能设置"
                          action={
                            <Button variant="ghost" size="sm" className="rounded-lg">
                              配置
                              <ChevronRight className="w-4 h-4 ml-1" />
                            </Button>
                          }
                        />
                        <SettingCard
                          icon={<Globe className="w-5 h-5" />}
                          title="语言和地区"
                          description="选择您的首选语言"
                          action={
                            <Button variant="ghost" size="sm" className="rounded-lg">
                              中文（简体）
                              <ChevronRight className="w-4 h-4 ml-1" />
                            </Button>
                          }
                        />
                      </div>
                      
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">关于</h3>
                        <SettingCard
                          icon={<Info className="w-5 h-5" />}
                          title="版本信息"
                          description="CharMing Reader v1.0.0"
                          action={
                            <Button variant="ghost" size="sm" className="rounded-lg">
                              <HelpCircle className="w-4 h-4 mr-1" />
                              帮助与支持
                            </Button>
                          }
                        />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
            
            {/* Footer */}
            <div className="p-4 border-t bg-gray-50/50 flex items-center justify-between">
              <div className="text-xs text-gray-400">
                © 2024 CharMing Reader. All rights reserved.
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg"
              >
                <LogOut className="w-4 h-4 mr-2" />
                退出登录
              </Button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

interface SettingCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  action: React.ReactNode;
}

const SettingCard: React.FC<SettingCardProps> = ({ icon, title, description, action }) => (
  <motion.div
    whileHover={{ scale: 1.01 }}
    className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-sm transition-all"
  >
    <div className="flex items-center gap-4 flex-1">
      <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center text-blue-600">
        {icon}
      </div>
      <div className="flex-1">
        <h4 className="font-medium text-gray-900">{title}</h4>
        <p className="text-sm text-gray-500 mt-0.5">{description}</p>
      </div>
    </div>
    <div className="ml-4">
      {action}
    </div>
  </motion.div>
);

