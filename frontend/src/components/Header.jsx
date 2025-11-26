import React, {useState} from 'react';
import { Search, Bell, User, Play, Square } from 'lucide-react';

const Header = ({ agentStatus, onTriggerCheck, onStopCheck, onSearch, onClearSearch }) => {
  const getStatusIndicator = () => {
    switch (agentStatus) {
      case 'Processing':
        return { color: 'bg-yellow-400', text: 'Processing' };
      case 'Idle':
        return { color: 'bg-green-400', text: 'Idle' };
      case 'Error':
        return { color: 'bg-red-500', text: 'Error' };
      default:
        return { color: 'bg-gray-400', text: 'Connecting...' };
    }
  };

  const { color, text } = getStatusIndicator();

  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    } else {
      onClearSearch();
    }
  };

  const handleChange = (e) => {
    const value = e.target.value;
    setQuery(value);
    if (!value.trim()) {
      onClearSearch();
    }
  };

  return (
    <header className="flex-shrink-0 h-16 flex items-center justify-between px-4 md:px-6 border-b border-gray-200 dark:border-gray-700/80">
      <div className="flex items-center gap-2">
        <span className={`w-2.5 h-2.5 rounded-full ${color}`}></span>
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Agent Status: {text}</span>
      </div>
      {/* --- Global Search Bar --- */}
      <div className="w-full max-w-md">
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="search"
            value={query}
            onChange={handleChange}
            placeholder="Search emails, Drive, and knowledge base..."
            className="w-full pl-10 pr-4 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500"
          />
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search size={18} className="text-gray-400 dark:text-gray-500" />
          </div>
        </form>
      </div>
      <div>
        {agentStatus === 'Processing' ? (
            <button onClick={onStopCheck} className="bg-red-600 text-white px-3 py-1.5 rounded-lg hover:bg-red-700 flex items-center justify-center text-sm font-semibold transition-colors duration-200 shadow-sm">
                <Square size={14} className="mr-2" />Stop Processing
            </button>
        ) : (
            <button onClick={onTriggerCheck} className="bg-indigo-600 text-white px-3 py-1.5 rounded-lg hover:bg-indigo-700 flex items-center justify-center text-sm font-semibold transition-colors duration-200 shadow-sm">
                <Play size={14} className="mr-2" />Check Emails
            </button>
        )}
      </div>
    </header>
  );
};

export default Header;
