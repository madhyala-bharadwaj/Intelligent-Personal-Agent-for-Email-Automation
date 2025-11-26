import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Search, Star, Loader2, Inbox, ChevronLeft, ChevronRight, Trash2, Send } from 'lucide-react';
import toast from 'react-hot-toast';
import SmartReply from './SmartReply.jsx';

const formatDate = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    const today = new Date();
    const isToday = date.toDateString() === today.toDateString();
    if (isToday) {
        return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
    }
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const EmptyState = ({ icon, title, message }) => (
    <div className="text-center py-12 col-span-full">
        <div className="mx-auto w-16 h-16 bg-gray-100 dark:bg-gray-700/50 rounded-full flex items-center justify-center text-gray-400 dark:text-gray-500">
            {icon}
        </div>
        <h3 className="mt-4 text-lg font-semibold text-gray-800 dark:text-gray-100">{title}</h3>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{message}</p>
    </div>
);

const getSenderName = (from) => {
    if (!from) return '';
    const match = from.match(/(.*)<.*>/);
    if (match && match[1]) {
        return match[1].replace(/"/g, '').trim();
    }
    return from;
};

const EmailRow = ({ email, onStar, onUnstar, onDelete, onToggle, isExpanded, fullContent, isContentLoading, calculatedBodyHeight, smartReplies, onSelectSmartReply }) => {
    const handleStarClick = (e) => {
        e.stopPropagation();
        if (email.is_starred) {
            onUnstar(email.id);
        } else {
            onStar(email.id);
        }
    };

    const handleDeleteClick = (e) => {
        e.stopPropagation();
        onDelete(email.id);
    };
    
    const contentStyle = {
        maxHeight: isExpanded ? `${calculatedBodyHeight + 50}px` : '0px',
        overflow: 'hidden',
        transition: 'max-height 0.5s ease-in-out',
    };

    return (
        <div className="bg-white dark:bg-gray-800/50 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700/50 hover:border-indigo-500/50 transition-all duration-300 group">
            <div className="p-4 cursor-pointer" onClick={onToggle}>
                <div className="flex items-center gap-x-4">
                    <div className="flex-shrink-0 w-48 font-semibold text-gray-900 dark:text-gray-50 truncate pr-4">{getSenderName(email.from)}</div>
                    <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-700 dark:text-gray-200 truncate">{email.subject}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{email.snippet}</p>
                    </div>
                    <div className="flex-shrink-0 flex items-center ml-auto opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                         <button onClick={handleStarClick} className="p-2 text-gray-500 hover:text-yellow-500 dark:text-gray-400 dark:hover:text-yellow-400 rounded-full hover:bg-yellow-100 dark:hover:bg-yellow-500/20">
                            <Star size={16} className={email.is_starred ? 'text-yellow-400 fill-current' : ''} />
                        </button>
                        <button onClick={handleDeleteClick} className="p-2 text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 rounded-full hover:bg-red-100 dark:hover:bg-red-500/20">
                            <Trash2 size={16} />
                        </button>
                    </div>
                    <div className="flex-shrink-0 w-24 text-right text-xs text-gray-400 dark:text-gray-500 group-hover:hidden">{formatDate(email.timestamp)}</div>
                </div>
            </div>
            <div style={contentStyle}>
                <div className="px-4 pb-4 pt-2 border-t border-gray-200 dark:border-gray-700/80">
                    <div 
                        style={{ height: isExpanded ? `${calculatedBodyHeight}px` : '0px' }} 
                        className="bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700 transition-height duration-500 flex flex-col overflow-hidden"
                    >
                        {isContentLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <Loader2 size={24} className="animate-spin text-gray-400" />
                            </div>
                        ) : (
                            <>
                                <div className="flex-1 overflow-y-auto">
                                    <iframe
                                        srcDoc={fullContent || "<p>Could not load email content.</p>"}
                                        className="w-full h-full border-0"
                                        sandbox="allow-same-origin"
                                        title={`Email content for ${email.subject}`}
                                    />
                                </div>
                                <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700">
                                    <SmartReply suggestions={smartReplies} onSelectSuggestion={(suggestionText) => onSelectSmartReply(suggestionText, email)} />
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

const LabelView = ({ label, apiAction, onStar, onUnstar, onDelete, sendMessage, smartReplies, onSelectSmartReply, clearSmartReplies }) => {
    const [pages, setPages] = useState({});
    const [pageTokens, setPageTokens] = useState([null]);
    const [currentPageIndex, setCurrentPageIndex] = useState(0);
    
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [totalEmails, setTotalEmails] = useState(0);
    const [expandedEmailId, setExpandedEmailId] = useState(null);
    const [fullContent, setFullContent] = useState('');
    const [isContentLoading, setIsContentLoading] = useState(false);
    const [calculatedBodyHeight, setCalculatedBodyHeight] = useState(400);

    const scrollContainerRef = useRef(null);
    const ITEMS_PER_PAGE = 25;

    useEffect(() => {
        setPages({});
        setPageTokens([null]);
        setCurrentPageIndex(0);
        setExpandedEmailId(null);
    }, [label, searchQuery]);

    const currentToken = pageTokens[currentPageIndex];
    const currentPageData = pages[currentToken];
    const emails = currentPageData?.emails || [];
    const nextPageToken = currentPageData?.nextPageToken;

    useEffect(() => {
        if (!pages[currentToken]) {
            setIsLoading(true);
            apiAction(`/api/emails-by-label/${label.id}?query=${searchQuery}&page_token=${currentToken || ''}`)
                .then(response => {
                    setPages(prev => ({ ...prev, [currentToken]: { emails: response.emails, nextPageToken: response.nextPageToken } }));
                    setTotalEmails(response.total);
                })
                .catch(error => toast.error(`Failed to load emails for label "${label.name}".`))
                .finally(() => setIsLoading(false));
        } else {
            setIsLoading(false);
        }
    }, [currentPageIndex, pageTokens, label, searchQuery, apiAction, pages, currentToken]);

    const handleNextPage = () => {
        if (!nextPageToken) return;
        const nextPageIndex = currentPageIndex + 1;
        if (nextPageIndex >= pageTokens.length) {
            setPageTokens(prev => [...prev, nextPageToken]);
        }
        setCurrentPageIndex(nextPageIndex);
    };

    const handlePrevPage = () => {
        if (currentPageIndex > 0) {
            setCurrentPageIndex(prev => prev - 1);
        }
    };

    const handleToggleEmail = async (id) => {
        const newExpandedId = expandedEmailId === id ? null : id;
        setExpandedEmailId(newExpandedId);
        clearSmartReplies();

        if (newExpandedId) {
            // Request new smart replies
            sendMessage({
                type: 'get_smart_replies',
                payload: { emailId: id }
            });

            if (scrollContainerRef.current) {
                const containerHeight = scrollContainerRef.current.clientHeight;
                const rowHeaderHeight = 75;
                const verticalPadding = 40;
                const newHeight = containerHeight - rowHeaderHeight - verticalPadding;
                setCalculatedBodyHeight(Math.max(250, newHeight));
            }

            setIsContentLoading(true);
            setFullContent('');
            try {
                const response = await apiAction(`/api/actions/get-email-content/${id}`);
                setFullContent(response.content);
            } catch (error) {
                toast.error("Failed to load email content.");
                setFullContent("Error: Could not load content.");
            } finally {
                setIsContentLoading(false);
            }
        }
    };

    const startItem = currentPageIndex * ITEMS_PER_PAGE + 1;
    const endItem = Math.min((currentPageIndex + 1) * ITEMS_PER_PAGE, totalEmails);

    return (
        <div className="p-6 pb-2 bg-gray-50 dark:bg-gray-900/50 rounded-xl h-full flex flex-col">
            <div className="flex justify-between items-center mb-3">
                <div>
                    <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">Label: {label.name}</h1>
                    <p className="mt-1 text-gray-600 dark:text-gray-400">Browsing all emails with this label.</p>
                </div>
                <div className="relative w-full max-w-xs">
                    <input type="text" placeholder="Search in this label..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full pl-10 pr-4 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500"/>
                    <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/>
                </div>
            </div>
            <div ref={scrollContainerRef} className="flex-1 overflow-y-auto pr-2 -mr-2">
                {isLoading ? (
                    <div className="flex items-center justify-center h-full">
                        <Loader2 size={32} className="animate-spin text-indigo-500" />
                    </div>
                ) : emails.length > 0 ? (
                    <div className="space-y-2">
                        {emails.map(email => (
                            <EmailRow 
                                key={email.id} 
                                email={email} 
                                onStar={onStar}
                                onUnstar={onUnstar}
                                onDelete={onDelete}
                                onToggle={() => handleToggleEmail(email.id)}
                                isExpanded={expandedEmailId === email.id}
                                fullContent={fullContent}
                                isContentLoading={isContentLoading}
                                calculatedBodyHeight={calculatedBodyHeight}
                                smartReplies={expandedEmailId === email.id ? smartReplies : []}
                                onSelectSmartReply={onSelectSmartReply}
                            />
                        ))}
                    </div>
                ) : (
                    <EmptyState 
                        icon={<Inbox size={32} />}
                        title={searchQuery ? "No Results Found" : "This Label is Empty"}
                        message={searchQuery ? "Try a different search term." : "There are no emails with this label."}
                    />
                )}
            </div>
            <div className="flex items-center justify-end mt-4 text-sm text-gray-600 dark:text-gray-400">
                <span>{startItem}-{endItem} of {totalEmails}</span>
                <div className="flex items-center ml-4">
                    <button onClick={handlePrevPage} disabled={currentPageIndex === 0} className="p-1 disabled:opacity-50">
                        <ChevronLeft size={20} />
                    </button>
                    <button onClick={handleNextPage} disabled={!nextPageToken} className="p-1 disabled:opacity-50">
                        <ChevronRight size={20} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default LabelView;

