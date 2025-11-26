import React, { useState, useMemo, useEffect } from 'react';
import { X, Check, Lightbulb, FileText, Send, Loader2, Eye, Trash2, Bell, ChevronDown, Search, Inbox, Star, MessageSquare, ChevronLeft, ChevronRight } from 'lucide-react';
import toast from 'react-hot-toast';
import AnimateHeight from 'react-animate-height';

// --- Pagination Component ---
const PaginationControls = ({ currentPage, itemsPerPage, totalItems, onPageChange }) => {
    const totalPages = Math.ceil(totalItems / itemsPerPage);
    if (totalPages <= 1) return null;

    const startItem = currentPage * itemsPerPage + 1;
    const endItem = Math.min((currentPage + 1) * itemsPerPage, totalItems);

    return (
        <div className="flex items-center justify-end mt-4 text-sm text-gray-600 dark:text-gray-400">
            <span>{startItem}-{endItem} of {totalItems}</span>
            <div className="flex items-center ml-4">
                <button 
                    onClick={() => onPageChange(currentPage - 1)} 
                    disabled={currentPage === 0}
                    className="p-1 disabled:opacity-50"
                >
                    <ChevronLeft size={20} />
                </button>
                <button 
                    onClick={() => onPageChange(currentPage + 1)} 
                    disabled={currentPage >= totalPages - 1}
                    className="p-1 disabled:opacity-50"
                >
                    <ChevronRight size={20} />
                </button>
            </div>
        </div>
    );
};


const formatDate = (timestamp) => {
    if (!timestamp) return '';
    
    const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp * 1000);

    if (isNaN(date.getTime())) {
        return 'Invalid Date';
    }

    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const dateDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());

    if (dateDay.getTime() === today.getTime()) {
        return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    }
    if (dateDay.getTime() === yesterday.getTime()) {
        return 'Yesterday';
    }
    if (now.getFullYear() === date.getFullYear()) {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
};


const groupItemsByDate = (items) => {
    const groups = { Today: [], Yesterday: [], 'This Week': [], Older: [] };
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const thisWeek = new Date(today);
    thisWeek.setDate(thisWeek.getDate() - now.getDay());

    items.forEach(item => {
        if (!item.timestamp) {
            groups.Older.push(item);
            return;
        }
        const itemDate = typeof item.timestamp === 'string' ? new Date(item.timestamp) : new Date(item.timestamp * 1000);
        if (isNaN(itemDate.getTime())) {
            groups.Older.push(item);
            return;
        }
        const itemDay = new Date(itemDate.getFullYear(), itemDate.getMonth(), itemDate.getDate());

        if (itemDay.getTime() === today.getTime()) groups.Today.push(item);
        else if (itemDay.getTime() === yesterday.getTime()) groups.Yesterday.push(item);
        else if (itemDay >= thisWeek) groups['This Week'].push(item);
        else groups.Older.push(item);
    });
    return groups;
};

const DateHeader = ({ text }) => (
    <div className="pt-4 pb-2">
        <h3 className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">{text}</h3>
    </div>
);

const EmptyState = ({ icon, title, message }) => (
    <div className="text-center py-12 col-span-full">
        <div className="mx-auto w-16 h-16 bg-gray-100 dark:bg-gray-700/50 rounded-full flex items-center justify-center text-gray-400 dark:text-gray-500">
            {icon}
        </div>
        <h3 className="mt-4 text-lg font-semibold text-gray-800 dark:text-gray-100">{title}</h3>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{message}</p>
    </div>
);

const LoadingSkeleton = () => (
    <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
            <div key={i} className="p-4 bg-white dark:bg-gray-800 rounded-xl shadow-sm animate-pulse">
                <div className="flex items-center">
                    <div className="w-10 h-10 rounded-lg bg-gray-200 dark:bg-gray-700 mr-4"></div>
                    <div className="flex-1 space-y-2">
                        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                    </div>
                </div>
            </div>
        ))}
    </div>
);

const BulkActionBar = ({ selectedCount, onClear, children }) => (
    <div className="flex items-center justify-between p-2 mb-3 bg-indigo-50 dark:bg-indigo-500/10 rounded-lg">
        <span className="text-sm font-semibold text-indigo-700 dark:text-indigo-300">{selectedCount} items selected</span>
        <div className="flex items-center space-x-2">
            {children}
            <button onClick={onClear} className="p-1 text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-100"><X size={16} /></button>
        </div>
    </div>
);

const ActionCard = ({ icon, title, subtitle, children, isExpanded, onToggle, isSeen, isSelected, onSelect, actionButton, date }) => (
  <div className={`relative transition-all duration-300 rounded-xl border dark:border-gray-700/50 bg-white dark:bg-gray-800 shadow-md hover:shadow-xl hover:-translate-y-1 ${isSeen ? 'opacity-60' : ''} ${isSelected ? 'border-indigo-500' : 'border-transparent'}`}>
    <div className="absolute top-3 left-3">
      <div className="pt-4 pb-4 pr-4 flex items-center cursor-pointer">
        <input type="checkbox" checked={isSelected} onChange={onSelect} className="h-4 w-4 rounded text-indigo-600 focus:ring-indigo-500" />
      </div>
    </div>
    <div className="p-4 pl-10 cursor-pointer" onClick={onToggle}>
      <div className="flex items-center">
        <div className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center mr-4">
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-gray-800 dark:text-gray-100 truncate">{title}</div>
          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{subtitle}</p>
        </div>
        <div className="flex items-center ml-4">
            <span className="text-xs text-gray-400 dark:text-gray-500 w-20 text-right">{date}</span>
            {actionButton}
            <ChevronDown size={20} className={`text-gray-400 dark:text-gray-500 transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`} />
        </div>
      </div>
    </div>
    <AnimateHeight duration={300} height={isExpanded ? 'auto' : 0}>
      <div className="px-4 pb-4 pt-2 border-t border-gray-200 dark:border-gray-700/80">
        {children}
      </div>
    </AnimateHeight>
  </div>
);

const DraftCard = ({ draft, isExpanded, onToggle, onSend, onReject, isProcessing, isSelected, onSelect }) => {
  const [editedBody, setEditedBody] = useState(draft.body);
  useEffect(() => { setEditedBody(draft.body); }, [draft.body]);
  const handleSend = () => onSend(draft.id, editedBody);

  return (
    <ActionCard
      icon={<div className="w-full h-full rounded-lg bg-blue-100 dark:bg-blue-500/20 flex items-center justify-center"><FileText className="text-blue-500" size={20}/></div>}
      title={draft.from}
      subtitle={draft.subject}
      isExpanded={isExpanded}
      onToggle={onToggle}
      isSelected={isSelected}
      onSelect={onSelect}
      date={formatDate(draft.timestamp)}
    >
      <div className="space-y-3">
        <div className="bg-gray-50 dark:bg-gray-900/50 p-3 rounded-lg">
          <h4 className="text-xs font-bold text-gray-500 dark:text-gray-400 mb-1 tracking-wider">ORIGINAL SUMMARY</h4>
          <p className="text-sm text-gray-700 dark:text-gray-300 italic">
            {draft.summary && draft.summary !== "Summary not available." ? draft.summary : "Summary not available for this older draft."}
          </p>
        </div>
        <div className="flex flex-col">
          <textarea value={editedBody} onChange={(e) => setEditedBody(e.target.value)} className="w-full h-48 p-3 text-sm border rounded-lg bg-white dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600 focus:ring-2 focus:ring-indigo-500 transition-shadow"/>
          <div className="flex justify-end space-x-3 mt-3">
            <button onClick={() => onReject(draft.id)} disabled={isProcessing} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors">Reject</button>
            <button onClick={handleSend} disabled={isProcessing} className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800 disabled:opacity-50 flex items-center transition-colors">
              {isProcessing ? <Loader2 size={16} className="animate-spin mr-2"/> : <Send size={16} className="mr-2"/>} Send
            </button>
          </div>
        </div>
      </div>
    </ActionCard>
  );
};

const LearningCard = ({ proposal, isExpanded, onToggle, onApprove, onReject, isProcessing, isSelected, onSelect }) => (
    <ActionCard
      icon={<div className="w-full h-full rounded-lg bg-yellow-100 dark:bg-yellow-500/20 flex items-center justify-center"><Lightbulb className="text-yellow-500" size={20}/></div>}
      title="Learning Proposal"
      subtitle={`From: ${proposal.fromEmail}`}
      isExpanded={isExpanded}
      onToggle={onToggle}
      isSelected={isSelected}
      onSelect={onSelect}
      date={formatDate(proposal.timestamp)}
    >
        <p className="text-sm text-gray-700 dark:text-gray-300 my-2 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">Fact: "{proposal.fact}"</p>
        <div className="flex justify-end space-x-3 mt-2">
            <button onClick={() => onReject(proposal.id)} disabled={isProcessing} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 flex items-center"><X size={16} className="mr-2"/> Reject</button>
            <button onClick={() => onApprove(proposal.id)} disabled={isProcessing} className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center"><Check size={16} className="mr-2"/> Approve</button>
        </div>
    </ActionCard>
);

const PriorityCard = ({ item, isExpanded, onToggle, onDismiss, onKeep, onStar, isProcessing, isSelected, onSelect, onContextualChat, fullContent, isContentLoading }) => (
    <ActionCard
        icon={<div className="w-full h-full rounded-lg bg-red-100 dark:bg-red-500/20 flex items-center justify-center"><Bell className="text-red-500" size={20}/></div>}
        title={
            <div className="flex items-center gap-2">
                <span className="truncate">{item.from}</span>
                {item.seen && <Eye size={14} className="text-gray-400 dark:text-gray-500 flex-shrink-0" />}
            </div>
        }
        subtitle={item.subject}
        isExpanded={isExpanded}
        onToggle={onToggle}
        isSeen={item.seen}
        isSelected={isSelected}
        onSelect={onSelect}
        date={formatDate(item.timestamp)}
        actionButton={
            <>
                <button onClick={(e) => { e.stopPropagation(); onContextualChat(`Summarize the thread for message ID ${item.id}`); }} className="p-2 text-gray-500 hover:text-indigo-600 dark:text-gray-400 dark:hover:text-indigo-400 rounded-full hover:bg-indigo-100 dark:hover:bg-indigo-500/20">
                    <MessageSquare size={16} />
                </button>
                <button onClick={(e) => { e.stopPropagation(); onStar(item.id); }} disabled={isProcessing} className="p-2 text-gray-500 hover:text-yellow-500 dark:text-gray-400 dark:hover:text-yellow-400 rounded-full hover:bg-yellow-100 dark:hover:bg-yellow-500/20">
                    <Star size={16} className={item.is_starred ? 'text-yellow-400 fill-current' : ''} />
                </button>
            </>
        }
    >
        <div className="space-y-3">
            <p className="text-sm text-gray-700 dark:text-gray-300 my-2 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">Summary: "{item.summary || 'N/A'}"</p>
            <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg h-64 overflow-y-auto border border-gray-200 dark:border-gray-700">
                {isContentLoading ? (
                    <div className="flex items-center justify-center h-full">
                        <Loader2 size={24} className="animate-spin text-gray-400" />
                    </div>
                ) : (
                    <iframe
                        srcDoc={fullContent || "<p>Click to load email content.</p>"}
                        className="w-full h-full border-0"
                        sandbox="allow-same-origin"
                        title={`Email content for ${item.subject}`}
                    />
                )}
            </div>
            <div className="flex justify-end space-x-3 mt-2">
                {item.seen ? (
                    <button onClick={() => onDismiss(item.id)} disabled={isProcessing} className="w-full px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center justify-center"><Trash2 size={16} className="mr-2"/> Dismiss</button>
                ) : (
                    <>
                        <button onClick={() => onKeep(item.id)} disabled={isProcessing} className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 flex items-center justify-center"><Eye size={16} className="mr-2"/> Keep</button>
                        <button onClick={() => onDismiss(item.id)} disabled={isProcessing} className="flex-1 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center"><Trash2 size={16} className="mr-2"/> Dismiss</button>
                    </>
                )}
            </div>
        </div>
    </ActionCard>
);

const StarredCard = ({ item, isExpanded, onToggle, onUnstar, isProcessing, isSelected, onSelect, fullContent, isContentLoading, onContextualChat }) => (
    <ActionCard
        icon={<div className="w-full h-full rounded-lg bg-yellow-100 dark:bg-yellow-500/20 flex items-center justify-center"><Star className="text-yellow-500" size={20}/></div>}
        title={item.from}
        subtitle={item.subject}
        isExpanded={isExpanded}
        onToggle={onToggle}
        isSelected={isSelected}
        onSelect={onSelect}
        date={formatDate(item.timestamp)}
        actionButton={
            <button onClick={(e) => { e.stopPropagation(); onContextualChat(`What are the key points of the email from ${item.from} about "${item.subject}"?`); }} className="p-2 text-gray-500 hover:text-indigo-600 dark:text-gray-400 dark:hover:text-indigo-400 rounded-full hover:bg-indigo-100 dark:hover:bg-indigo-500/20">
                <MessageSquare size={16} />
            </button>
        }
    >
        <div className="space-y-3">
            <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg h-64 overflow-y-auto border border-gray-200 dark:border-gray-700">
                {isContentLoading ? (
                    <div className="flex items-center justify-center h-full">
                        <Loader2 size={24} className="animate-spin text-gray-400" />
                    </div>
                ) : (
                    <iframe
                        srcDoc={fullContent || "<p>Could not load email content.</p>"}
                        className="w-full h-full border-0"
                        sandbox="allow-same-origin"
                        title={`Email content for ${item.subject}`}
                    />
                )}
            </div>
            <div className="flex justify-end">
                <button onClick={() => onUnstar(item.id)} disabled={isProcessing} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 flex items-center">
                    {isProcessing ? <Loader2 size={16} className="animate-spin mr-2"/> : <Star size={16} className="mr-2"/>} Unstar
                </button>
            </div>
        </div>
    </ActionCard>
);


const ActionQueue = ({ isLoading, drafts, learningProposals, priorityItems, starredItems, selectedItems, setSelectedItems, confirmAction, onBulkDismiss, onBulkKeep, onBulkRejectDrafts, onBulkApproveLearnings, onBulkRejectLearnings, onBulkUnstar, handleSendDraft, handleRejectDraft, handleApproveLearning, handleRejectLearning, handleDismissPriority, handleKeepPriority, handleStarEmail, handleUnstarEmail, handleGetEmailContent, onContextualChat }) => {
  const [expandedItemId, setExpandedItemId] = useState(null);
  const [activeTab, setActiveTab] = useState('priority');
  const [searchQuery, setSearchQuery] = useState('');
  const [processingItems, setProcessingItems] = useState(new Set());
  const [expandedEmailContent, setExpandedEmailContent] = useState('');
  const [isContentLoading, setIsContentLoading] = useState(false);
  const [pagination, setPagination] = useState({
      priority: 0,
      starred: 0,
      drafts: 0,
      learning: 0
  });

  const ITEMS_PER_PAGE = 10;

  useEffect(() => {
    setSelectedItems(new Set());
    setPagination(prev => ({ ...prev, [activeTab]: 0 }));
  }, [activeTab, setSelectedItems]);

  const sortedPriorityItems = useMemo(() => [...priorityItems].sort((a, b) => (a.seen === b.seen) ? 0 : a.seen ? 1 : -1), [priorityItems]);

  const createConfirmedActionHandler = (handler, { title, message, success, error }) => (id) => {
      confirmAction(title, message, async () => {
          setProcessingItems(prev => new Set(prev).add(id));
          try {
              await handler(id);
              toast.success(success);
          } catch (err) {
              toast.error(`${error}: ${err.message}`);
          } finally {
              setProcessingItems(prev => {
                  const newSet = new Set(prev);
                  newSet.delete(id);
                  return newSet;
              });
          }
      });
  };

  const createActionHandler = (handler, { success, error }) => async (id, ...args) => {
    setProcessingItems(prev => new Set(prev).add(id));
    try {
        await handler(id, ...args);
        toast.success(success);
    } catch (err) {
        toast.error(`${error}: ${err.message}`);
    } finally {
        setProcessingItems(prev => {
            const newSet = new Set(prev);
            newSet.delete(id);
            return newSet;
        });
    }
  };

  const onSendDraft = createActionHandler(handleSendDraft, { success: "Draft sent!", error: "Failed to send draft" });
  const onRejectDraft = createConfirmedActionHandler(handleRejectDraft, { title: "Reject Draft?", message: "This will delete the draft and cannot be undone.", success: "Draft rejected.", error: "Failed to reject draft" });
  const onApproveLearning = createActionHandler(handleApproveLearning, { success: "Fact learned!", error: "Failed to learn fact" });
  const onRejectLearning = createConfirmedActionHandler(handleRejectLearning, { title: "Reject Learning?", message: "Are you sure you want to reject this learning proposal?", success: "Learning rejected.", error: "Failed to reject learning" });
  const onKeepPriority = createActionHandler(handleKeepPriority, { success: "Priority item acknowledged.", error: "Failed to acknowledge item" });
  const onDismissPriority = createConfirmedActionHandler(handleDismissPriority, { title: "Dismiss Priority Item?", message: "This will remove the item from the queue.", success: "Item dismissed.", error: "Failed to dismiss item" });
  const onStarEmail = createActionHandler(handleStarEmail, { success: "Email starred!", error: "Failed to star email" });
  const onUnstarEmail = createConfirmedActionHandler(handleUnstarEmail, { title: "Unstar Email?", message: "This will remove the star from this email.", success: "Email unstarred.", error: "Failed to unstar email" });

  const handleSelectItem = (id) => {
    setSelectedItems(prev => {
        const newSet = new Set(prev);
        if (newSet.has(id)) {
            newSet.delete(id);
        } else {
            newSet.add(id);
        }
        return newSet;
    });
  };

  const handleToggle = async (id) => {
    const newExpandedId = expandedItemId === id ? null : id;
    setExpandedItemId(newExpandedId);

    if (newExpandedId && (activeTab === 'starred' || activeTab === 'priority')) {
        setIsContentLoading(true);
        setExpandedEmailContent('');
        try {
            const response = await handleGetEmailContent(id);
            setExpandedEmailContent(response.content);
        } catch (error) {
            toast.error("Failed to load email content.");
            setExpandedEmailContent("Error: Could not load content.");
        } finally {
            setIsContentLoading(false);
        }
    }
  };

  const filteredContent = useMemo(() => {
    const lowercasedQuery = searchQuery.toLowerCase();
    if (!lowercasedQuery) {
        return {
            priority: sortedPriorityItems,
            drafts: drafts,
            learning: learningProposals,
            starred: starredItems
        };
    }
    return {
        priority: sortedPriorityItems.filter(p => p.from.toLowerCase().includes(lowercasedQuery) || p.subject.toLowerCase().includes(lowercasedQuery) || (p.summary && p.summary.toLowerCase().includes(lowercasedQuery))),
        drafts: drafts.filter(d => d.from.toLowerCase().includes(lowercasedQuery) || d.subject.toLowerCase().includes(lowercasedQuery) || (d.summary && d.summary.toLowerCase().includes(lowercasedQuery))),
        learning: learningProposals.filter(l => l.fromEmail.toLowerCase().includes(lowercasedQuery) || l.fact.toLowerCase().includes(lowercasedQuery)),
        starred: starredItems.filter(s => s.from.toLowerCase().includes(lowercasedQuery) || s.subject.toLowerCase().includes(lowercasedQuery) || (s.snippet && s.snippet.toLowerCase().includes(lowercasedQuery)))
    };
  }, [searchQuery, sortedPriorityItems, drafts, learningProposals, starredItems]);

  const renderBulkActions = () => {
    switch(activeTab) {
        case 'priority':
            return (
                <>
                    <button onClick={onBulkKeep} className="px-3 py-1 text-xs font-medium text-gray-700 bg-white rounded-md hover:bg-gray-100 border dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600">Acknowledge</button>
                    <button onClick={onBulkDismiss} className="px-3 py-1 text-xs font-medium text-red-700 bg-red-100 rounded-md hover:bg-red-200">Dismiss</button>
                </>
            );
        case 'drafts':
            return <button onClick={onBulkRejectDrafts} className="px-3 py-1 text-xs font-medium text-red-700 bg-red-100 rounded-md hover:bg-red-200">Reject Selected</button>;
        case 'learning':
            return (
                <>
                    <button onClick={onBulkApproveLearnings} className="px-3 py-1 text-xs font-medium text-green-700 bg-green-100 rounded-md hover:bg-green-200">Approve</button>
                    <button onClick={onBulkRejectLearnings} className="px-3 py-1 text-xs font-medium text-red-700 bg-red-100 rounded-md hover:bg-red-200">Reject</button>
                </>
            );
        case 'starred':
            return <button onClick={onBulkUnstar} className="px-3 py-1 text-xs font-medium text-yellow-800 bg-yellow-100 rounded-md hover:bg-yellow-200">Unstar Selected</button>;
        default:
            return null;
    }
  };

  const renderContent = () => {
    if (isLoading) return <LoadingSkeleton />;

    const contentMap = {
        priority: filteredContent.priority,
        drafts: filteredContent.drafts,
        learning: filteredContent.learning,
        starred: filteredContent.starred
    };
    
    const activeItems = contentMap[activeTab] || [];
    const currentPage = pagination[activeTab] || 0;
    const paginatedItems = activeItems.slice(currentPage * ITEMS_PER_PAGE, (currentPage + 1) * ITEMS_PER_PAGE);
    
    if (activeItems.length === 0) {
        return <EmptyState 
            icon={searchQuery ? <Search size={24}/> : <Inbox size={24}/>}
            title={searchQuery ? "No Results Found" : "All Caught Up!"}
            message={searchQuery ? "Try a different search term." : `There are no items in the ${activeTab} queue.`}
        />;
    }

    const CardComponent = {
        priority: PriorityCard,
        drafts: DraftCard,
        learning: LearningCard,
        starred: StarredCard
    }[activeTab];

    const renderGroupedList = (items) => {
        const grouped = groupItemsByDate(items);
        return Object.entries(grouped).map(([groupName, groupItems]) =>
            groupItems.length > 0 ? (
                <div key={groupName}>
                    <DateHeader text={groupName} />
                    <div className="space-y-3">
                        {groupItems.map(item => <CardComponent key={item.id} item={item} draft={item} proposal={item} isProcessing={processingItems.has(item.id)} isSelected={selectedItems.has(item.id)} onSelect={() => handleSelectItem(item.id)} isExpanded={expandedItemId === item.id} onToggle={() => handleToggle(item.id)} onSend={onSendDraft} onReject={onRejectDraft} onApprove={onApproveLearning} onRejectLearning={onRejectLearning} onDismiss={onDismissPriority} onKeep={onKeepPriority} onStar={onStarEmail} onUnstar={onUnstarEmail} fullContent={expandedEmailContent} isContentLoading={isContentLoading} onContextualChat={onContextualChat} />)}
                    </div>
                </div>
            ) : null
        );
    };
    
    if (activeTab === 'learning') {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {paginatedItems.map(item => <LearningCard key={item.id} proposal={item} isExpanded={expandedItemId === item.id} onToggle={() => handleToggle(item.id)} onApprove={onApproveLearning} onReject={onRejectLearning} isProcessing={processingItems.has(item.id)} isSelected={selectedItems.has(item.id)} onSelect={() => handleSelectItem(item.id)} />)}
            </div>
        );
    }
    
    return <div>{renderGroupedList(paginatedItems)}</div>;
  };

  return (
    <div className="bg-white dark:bg-gray-800/50 p-4 rounded-xl shadow-sm">
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-lg font-bold text-gray-800 dark:text-gray-100">Action Queue</h2>
        <div className="relative w-full max-w-xs">
            <input type="text" placeholder="Search queue..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full pl-10 pr-4 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500"/>
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/>
        </div>
      </div>
      
      {selectedItems.size > 0 && <BulkActionBar selectedCount={selectedItems.size} onClear={() => setSelectedItems(new Set())}>{renderBulkActions()}</BulkActionBar>}
      
      <div className="flex space-x-2 border-b border-gray-200 dark:border-gray-700 mb-4">
        <button onClick={() => setActiveTab('priority')} className={`px-3 py-2 text-sm font-semibold transition-colors relative ${activeTab === 'priority' ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}>
            Priority 
            <span className="ml-1.5 bg-red-100 text-red-600 text-xs font-bold px-2 py-0.5 rounded-full">{filteredContent.priority.length}</span>
            {activeTab === 'priority' && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500 rounded-t-full"></span>}
        </button>
        <button onClick={() => setActiveTab('starred')} className={`px-3 py-2 text-sm font-semibold transition-colors relative ${activeTab === 'starred' ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}>
            Starred
            <span className="ml-1.5 bg-yellow-100 text-yellow-700 text-xs font-bold px-2 py-0.5 rounded-full">{filteredContent.starred.length}</span>
            {activeTab === 'starred' && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500 rounded-t-full"></span>}
        </button>
        <button onClick={() => setActiveTab('drafts')} className={`px-3 py-2 text-sm font-semibold transition-colors relative ${activeTab === 'drafts' ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}>
            Drafts 
            <span className="ml-1.5 bg-blue-100 text-blue-600 text-xs font-bold px-2 py-0.5 rounded-full">{filteredContent.drafts.length}</span>
            {activeTab === 'drafts' && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500 rounded-t-full"></span>}
        </button>
        <button onClick={() => setActiveTab('learning')} className={`px-3 py-2 text-sm font-semibold transition-colors relative ${activeTab === 'learning' ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'}`}>
            Learning 
            <span className="ml-1.5 bg-yellow-100 text-yellow-700 text-xs font-bold px-2 py-0.5 rounded-full">{filteredContent.learning.length}</span>
            {activeTab === 'learning' && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500 rounded-t-full"></span>}
        </button>
      </div>
      <div>
        {renderContent()}
        <PaginationControls 
            currentPage={pagination[activeTab] || 0}
            itemsPerPage={ITEMS_PER_PAGE}
            totalItems={filteredContent[activeTab].length}
            onPageChange={(page) => setPagination(prev => ({...prev, [activeTab]: page}))}
        />
      </div>
    </div>
  );
};

export default ActionQueue;
