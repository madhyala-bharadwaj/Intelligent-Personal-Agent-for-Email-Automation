import React, { useState, useEffect } from 'react';
import { LayoutDashboard, BrainCircuit, Settings, Bot, Sun, Moon, Tag, ChevronDown } from 'lucide-react';
import AnimateHeight from 'react-animate-height';

const Sidebar = ({ activeView, setActiveView, theme, toggleTheme, labels, onLabelSelect, selectedLabelId }) => {
  const [isLabelsExpanded, setIsLabelsExpanded] = useState(true);
  
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { id: 'knowledge', label: 'Knowledge Base', icon: <BrainCircuit size={20} /> },
    { id: 'settings', label: 'Settings', icon: <Settings size={20} /> },
  ];

  return (
    <aside className="w-64 bg-white dark:bg-gray-800/50 border-r border-gray-200 dark:border-gray-700/50 flex flex-col p-4">
      <div className="flex items-center gap-3 mb-8">
        <Bot size={32} className="text-indigo-600 dark:text-indigo-400" />
        <h1 className="text-xl font-bold text-gray-800 dark:text-gray-100">Agent UI</h1>
      </div>
      <nav className="flex-1 space-y-2 overflow-y-auto no-scrollbar">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActiveView(item.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              activeView === item.id
                ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800 dark:text-gray-400 dark:hover:bg-gray-700/50 dark:hover:text-gray-200'
            }`}
          >
            {item.icon}
            <span>{item.label}</span>
          </button>
        ))}
        
        <div className="pt-4">
            <button onClick={() => setIsLabelsExpanded(!isLabelsExpanded)} className="w-full flex justify-between items-center text-sm font-semibold text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">
                <span>Labels</span>
                <ChevronDown size={16} className={`transition-transform ${isLabelsExpanded ? 'rotate-180' : ''}`} />
            </button>
            <AnimateHeight duration={300} height={isLabelsExpanded ? 'auto' : 0}>
                <div className="mt-2 space-y-1">
                    {labels.map(label => (
                        <button 
                            key={label.id} 
                            onClick={() => onLabelSelect(label)}
                            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                                activeView === 'label_view' && selectedLabelId === label.id
                                ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300'
                                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800 dark:text-gray-400 dark:hover:bg-gray-700/50 dark:hover:text-gray-200'
                            }`}
                        >
                            <Tag size={16} />
                            <span className="truncate">{label.name}</span>
                        </button>
                    ))}
                </div>
            </AnimateHeight>
        </div>

      </nav>
      <div className="mt-auto">
        <div className="flex items-center justify-between p-2 bg-gray-100 dark:bg-gray-700/50 rounded-lg">
          <span className="text-sm font-medium text-gray-600 dark:text-gray-300">Toggle Theme</span>
          <button onClick={toggleTheme} className="relative w-12 h-6 bg-gray-300 dark:bg-gray-600 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <span className={`absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform transform ${theme === 'dark' ? 'translate-x-6' : ''}`}>
                {theme === 'light' ? <Sun size={12} className="text-yellow-500 m-0.5"/> : <Moon size={12} className="text-indigo-300 m-0.5"/>}
            </span>
          </button>
        </div>
      </div>
      <style>{`.no-scrollbar::-webkit-scrollbar { display: none; }`}</style>
    </aside>
  );
};

export default Sidebar;
