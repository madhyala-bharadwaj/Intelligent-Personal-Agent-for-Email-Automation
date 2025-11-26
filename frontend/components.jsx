import React, { useMemo, useState, useRef, useEffect } from 'react';
import { FileText, Brain, AlertTriangle, Send, Trash2, Check, X, ChevronDown, Bot, User, Power, StopCircle, CornerDownLeft, ArrowUp } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

const ActionQueue = ({
    isLoading,
    drafts = [],
    learningProposals = [],
    priorityItems = [],
    selectedItems,
    setSelectedItems,
    onBulkDismiss,
    onBulkKeep,
    onBulkRejectDrafts,
    onBulkApproveLearnings,
    onBulkRejectLearnings,
    handleSendDraft,
    handleRejectDraft,
    handleApproveLearning,
    handleRejectLearning,
    handleDismissPriority,
    handleKeepPriority
}) => {
    const [activeTab, setActiveTab] = useState('priority');
    const [expandedItem, setExpandedItem] = useState(null);

    const tabs = useMemo(() => ({
        priority: { label: 'High Priority', data: priorityItems, icon: <AlertTriangle size={16} /> },
        drafts: { label: 'Drafts', data: drafts, icon: <FileText size={16} /> },
        learning: { label: 'Learning', data: learningProposals, icon: <Brain size={16} /> },
    }), [priorityItems, drafts, learningProposals]);

    const handleSelectAll = (e) => {
        if (e.target.checked) {
            const allIds = tabs[activeTab].data.map(item => item.id);
            setSelectedItems(new Set(allIds));
        } else {
            setSelectedItems(new Set());
        }
    };

    const handleSelectItem = (id) => {
        const newSelection = new Set(selectedItems);
        if (newSelection.has(id)) {
            newSelection.delete(id);
        } else {
            newSelection.add(id);
        }
        setSelectedItems(newSelection);
    };
    
    const renderItem = (item) => {
        const isExpanded = expandedItem === item.id;
        switch (activeTab) {
            case 'priority':
                return (
                    <div className="p-3">
                        <p className="text-sm text-gray-600 dark:text-gray-400">{item.summary}</p>
                        <div className="flex gap-2 mt-3">
                            <button onClick={() => handleDismissPriority(item.id)} className="px-3 py-1 text-xs font-semibold text-white bg-red-500 rounded-md hover:bg-red-600">Dismiss</button>
                            <button onClick={() => handleKeepPriority(item.id)} className="px-3 py-1 text-xs font-semibold text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500">Keep</button>
                        </div>
                    </div>
                );
            case 'drafts':
                return (
                    <div className="p-3">
                        <div className="prose prose-sm dark:prose-invert" dangerouslySetInnerHTML={{ __html: item.body }} />
                        <div className="flex gap-2 mt-3">
                            <button onClick={() => handleSendDraft(item.id, item.body)} className="px-3 py-1 text-xs font-semibold text-white bg-green-500 rounded-md hover:bg-green-600">Send</button>
                            <button onClick={() => handleRejectDraft(item.id)} className="px-3 py-1 text-xs font-semibold text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500">Reject</button>
                        </div>
                    </div>
                );
            case 'learning':
                return (
                    <div className="p-3">
                        <p className="text-sm text-gray-600 dark:text-gray-400"><strong>Fact to learn:</strong> {item.fact}</p>
                        <div className="flex gap-2 mt-3">
                            <button onClick={() => handleApproveLearning(item.id)} className="px-3 py-1 text-xs font-semibold text-white bg-green-500 rounded-md hover:bg-green-600">Approve</button>
                            <button onClick={() => handleRejectLearning(item.id)} className="px-3 py-1 text-xs font-semibold text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500">Reject</button>
                        </div>
                    </div>
                );
            default: return null;
        }
    };

    return (
        <div className="bg-white dark:bg-gray-800/50 rounded-xl shadow-sm h-full flex flex-col">
            {/* Header and Tabs */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-3">Action Queue</h2>
                <div className="flex space-x-1 border-b border-gray-200 dark:border-gray-700">
                    {Object.keys(tabs).map(tabKey => (
                        <button key={tabKey} onClick={() => setActiveTab(tabKey)} className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${activeTab === tabKey ? 'border-b-2 border-indigo-500 text-indigo-600 dark:text-indigo-400' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'}`}>
                            {tabs[tabKey].icon} {tabs[tabKey].label} ({tabs[tabKey].data.length})
                        </button>
                    ))}
                </div>
            </div>

            {/* Bulk Actions */}
            {selectedItems.size > 0 && (
                <div className="p-2 bg-gray-100 dark:bg-gray-900/50 flex items-center gap-3">
                    <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{selectedItems.size} selected</span>
                    {activeTab === 'priority' && <>
                        <button onClick={onBulkDismiss} className="px-2 py-1 text-xs text-white bg-red-500 rounded">Dismiss</button>
                        <button onClick={onBulkKeep} className="px-2 py-1 text-xs text-gray-700 bg-gray-200 rounded">Keep</button>
                    </>}
                    {activeTab === 'drafts' && <button onClick={onBulkRejectDrafts} className="px-2 py-1 text-xs text-white bg-red-500 rounded">Reject</button>}
                    {activeTab === 'learning' && <>
                        <button onClick={onBulkApproveLearnings} className="px-2 py-1 text-xs text-white bg-green-500 rounded">Approve</button>
                        <button onClick={onBulkRejectLearnings} className="px-2 py-1 text-xs text-white bg-red-500 rounded">Reject</button>
                    </>}
                </div>
            )}

            {/* Item List */}
            <div className="flex-1 overflow-y-auto p-2 no-scrollbar">
                {isLoading ? <p className="p-4 text-center text-gray-500">Loading items...</p> :
                 tabs[activeTab].data.length === 0 ? <p className="p-4 text-center text-gray-500">No items in this queue.</p> :
                 <table className="w-full text-sm">
                     <thead>
                         <tr className="border-b border-gray-200 dark:border-gray-700">
                             <th className="w-8 p-2"><input type="checkbox" onChange={handleSelectAll} checked={selectedItems.size === tabs[activeTab].data.length && tabs[active_tab].data.length > 0} /></th>
                             <th className="p-2 text-left font-semibold text-gray-600 dark:text-gray-300">From</th>
                             <th className="p-2 text-left font-semibold text-gray-600 dark:text-gray-300">Subject</th>
                             <th className="w-12 p-2"></th>
                         </tr>
                     </thead>
                     <tbody>
                        <AnimatePresence>
                         {tabs[activeTab].data.map(item => (
                            <React.Fragment key={item.id}>
                                <motion.tr 
                                    layout
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-900/50 cursor-pointer"
                                    onClick={() => setExpandedItem(expandedItem === item.id ? null : item.id)}
                                >
                                    <td className="p-2"><input type="checkbox" checked={selectedItems.has(item.id)} onChange={() => handleSelectItem(item.id)} onClick={e => e.stopPropagation()} /></td>
                                    <td className="p-2 text-gray-800 dark:text-gray-200 truncate max-w-xs">{item.from}</td>
                                    <td className="p-2 text-gray-800 dark:text-gray-200 truncate max-w-xs">{item.subject}</td>
                                    <td className="p-2">
                                        <ChevronDown size={16} className={`text-gray-400 transition-transform ${expandedItem === item.id ? 'rotate-180' : ''}`} />
                                    </td>
                                </motion.tr>
                                {expandedItem === item.id && (
                                    <motion.tr
                                        layout
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        exit={{ opacity: 0, height: 0 }}
                                    >
                                        <td colSpan="4" className="p-0 bg-gray-50 dark:bg-gray-900/50">
                                            {renderItem(item)}
                                        </td>
                                    </motion.tr>
                                )}
                            </React.Fragment>
                         ))}
                        </AnimatePresence>
                     </tbody>
                 </table>
                }
            </div>
        </div>
    );
};

export const ActivityFeed = ({ activityFeed = [] }) => (
    <div className="bg-white dark:bg-gray-800/50 rounded-xl shadow-sm h-full flex flex-col">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Activity Feed</h2>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3 no-scrollbar">
            {activityFeed.map((item, index) => (
                <div key={index} className="flex items-start gap-3 text-xs">
                    <span className="font-mono text-gray-400 dark:text-gray-500">{item.time}</span>
                    <p className={`flex-1 ${item.type === 'error' ? 'text-red-500' : 'text-gray-600 dark:text-gray-300'}`}>{item.message}</p>
                </div>
            ))}
        </div>
    </div>
);

export const ConversationalControl = ({ agentStatus, chatHistory = [], onSendMessage, onTriggerCheck, onStopCheck }) => {
    const [input, setInput] = useState('');
    const chatEndRef = useRef(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatHistory]);

    const handleSend = (e) => {
        e.preventDefault();
        if (input.trim()) {
            onSendMessage(input);
            setInput('');
        }
    };

    return (
        <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-800/50">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Conversational Control</h2>
                <p className="text-xs text-gray-500 dark:text-gray-400">Status: {agentStatus}</p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4 no-scrollbar">
                {chatHistory.map((msg, index) => (
                    <div key={index} className={`flex items-start gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                        {msg.role === 'agent' && <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center flex-shrink-0"><Bot size={18} className="text-indigo-500" /></div>}
                        <div className={`p-3 rounded-2xl max-w-sm ${msg.role === 'user' ? 'bg-blue-500 text-white rounded-br-lg' : 'bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-bl-lg'}`}>
                            <p className="text-sm">{msg.content}</p>
                        </div>
                        {msg.role === 'user' && <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center flex-shrink-0"><User size={18} /></div>}
                    </div>
                ))}
                <div ref={chatEndRef} />
            </div>
            
            <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-2 mb-2">
                    <button onClick={onTriggerCheck} className="flex-1 px-3 py-2 text-sm font-semibold text-white bg-green-500 rounded-lg hover:bg-green-600 flex items-center justify-center gap-2"><Power size={16}/> Start</button>
                    <button onClick={onStopCheck} className="flex-1 px-3 py-2 text-sm font-semibold text-white bg-red-500 rounded-lg hover:bg-red-600 flex items-center justify-center gap-2"><StopCircle size={16}/> Stop</button>
                </div>
                <form onSubmit={handleSend} className="relative">
                    <input 
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Chat with your agent..."
                        className="w-full pl-4 pr-12 py-3 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    <button type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:bg-indigo-300" disabled={!input.trim()}>
                        <ArrowUp size={18} />
                    </button>
                </form>
            </div>
        </div>
    );
};

export default ActionQueue;
