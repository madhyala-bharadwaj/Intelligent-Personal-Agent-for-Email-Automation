import React, { useState, useEffect, useRef } from 'react';
import toast, { Toaster } from 'react-hot-toast';

import Sidebar from './components/Sidebar';
import Header from './components/Header';
import { KnowledgeBaseView, SettingsView } from './components/Views';
import LabelView from './components/LabelView';
import ConfirmationModal from './components/ConfirmationModal';
import ActionQueue from './components/ActionQueue';
import ActivityFeed from './components/ActivityFeed';
import ConversationalControl from './components/ConversationalControl';
import SearchResults from './components/SearchResults';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

// --- Caching Helper Functions ---
const getCachedData = (key, defaultValue = []) => {
    try {
        const cached = localStorage.getItem(key);
        return cached ? JSON.parse(cached) : defaultValue;
    } catch (error) {
        console.error(`Error reading from localStorage for key "${key}":`, error);
        return defaultValue;
    }
};

const useCachedState = (key, defaultValue = []) => {
    const [state, setState] = useState(() => getCachedData(key, defaultValue));

    useEffect(() => {
        try {
            localStorage.setItem(key, JSON.stringify(state));
        } catch (error) {
            console.error(`Error writing to localStorage for key "${key}":`, error);
        }
    }, [key, state]);

    return [state, setState];
};


export default function App() {
  const [activeView, setActiveView] = useState('dashboard');
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');
  const [isLoading, setIsLoading] = useState(true);
  
  const [agentStatus, setAgentStatus] = useState('Connecting...');
  const [activityFeed, setActivityFeed] = useCachedState('activityFeed');
  const [drafts, setDrafts] = useCachedState('draftsQueue');
  const [learningProposals, setLearningProposals] = useCachedState('learningQueue');
  const [priorityItems, setPriorityItems] = useCachedState('priorityQueue');
  const [starredItems, setStarredItems] = useCachedState('starredQueue');
  const [chatHistory, setChatHistory] = useCachedState('chatHistory');
  const [chatInput, setChatInput] = useState(''); 
  const [labels, setLabels] = useCachedState('gmailLabels');
  const [selectedLabel, setSelectedLabel] = useState(null);
  const [smartReplies, setSmartReplies] = useState([]);
  
  const [selectedItems, setSelectedItems] = useState(new Set());

  const ws = useRef(null);
  const [modalState, setModalState] = useState({ isOpen: false, title: '', message: '', onConfirm: () => {} });
  const [knowledgeBase, setKnowledgeBase] = useState([]);
  const [settings, setSettings] = useState(null);

  const connectWebSocket = () => {
    ws.current = new WebSocket(WS_URL);
    console.log("Attempting to connect WebSocket...");

    ws.current.onopen = () => {
      console.log("WebSocket connected");
      setAgentStatus('Connected');
      setIsLoading(false);
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
       switch (data.type) {
        case 'initial_state':
          setAgentStatus(data.payload.agent_status);
          setActivityFeed(data.payload.activity_feed || []);
          setDrafts(data.payload.drafts_queue || []);
          setLearningProposals(data.payload.learning_queue || []);
          setPriorityItems(data.payload.priority_queue || []);
          setStarredItems(data.payload.starred_queue || []);
          setChatHistory(data.payload.chat_history || []);
          break;
        case 'smart_reply_suggestions':
          setSmartReplies(data.payload.suggestions || []);
          break;
        case 'starred_update':
          setStarredItems(data.payload);
          break;
        case 'drafts_update':
            setDrafts(data.payload);
            break;
        case 'priority_update':
            setPriorityItems(data.payload);
            break;
        case 'learning_update':
            setLearningProposals(data.payload);
            break;
        case 'log':
          setActivityFeed(prev => [data.payload, ...prev]);
          if(data.notification_type === 'new_draft') {
            toast.success("New draft created for review.");
          } else if (data.notification_type === 'priority_item') {
            toast.error("High-priority item detected!");
          }
          break;
        case 'status_update':
          setAgentStatus(data.payload.agent_status);
          break;
        case 'chat_update': 
          setChatHistory(prev => [...prev, data.payload]);
          break;
        case 'chat_history_cleared':
          setChatHistory([]);
          break;
        case 'update_priority_item':
            setPriorityItems(prev => prev.map(p => p.id === data.payload.id ? {...p, seen: data.payload.seen} : p));
            break;
        default:
          break;
      }
    };

    ws.current.onclose = () => {
      console.log("WebSocket disconnected. Attempting to reconnect in 3 seconds...");
      setAgentStatus("Disconnected");
      setTimeout(connectWebSocket, 3000);
    };

    ws.current.onerror = (err) => {
      console.error("WebSocket error:", err);
      setAgentStatus("Error");
      ws.current.close();
    };
  };

  const sendMessage = (message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify(message));
    } else {
        console.error("WebSocket is not connected.");
    }
  };


  useEffect(() => {
    setIsLoading(false); 
    connectWebSocket();
    
    const fetchInitialData = async () => {
        try {
            const [kbResponse, settingsResponse, labelsResponse] = await Promise.all([
                apiAction('/api/knowledge-base'),
                apiAction('/api/settings'),
                apiAction('/api/labels')
            ]);
            setKnowledgeBase(kbResponse);
            setSettings(settingsResponse);
            setLabels(labelsResponse);
        } catch (error) {
            toast.error("Failed to load initial data.");
        }
    };
    fetchInitialData();

    return () => {
        if (ws.current) {
            ws.current.onclose = null;
            ws.current.close();
        }
    }
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(theme === 'light' ? 'dark' : 'light');

  const apiAction = async (endpoint, options = {}) => {
      const response = await fetch(`${API_URL}${endpoint}`, options);
      if (!response.ok) {
          const errorData = await response.json().catch(() => ({ message: "Server responded with an error." }));
          throw new Error(errorData.detail || errorData.message);
      }
      return response.json();
  };

  const handleSendDraft = (messageId, body) => apiAction(`/api/actions/send-draft/${messageId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ body }) });
  const handleRejectDraft = (messageId) => apiAction(`/api/actions/discard-draft/${messageId}`, { method: 'DELETE' });
  const handleApproveLearning = (messageId) => apiAction(`/api/actions/approve-learning/${messageId}`, { method: 'POST' });
  const handleRejectLearning = (messageId) => apiAction(`/api/actions/reject-learning/${messageId}`, { method: 'POST' });
  const handleDismissPriority = (messageId) => apiAction(`/api/actions/dismiss-priority/${messageId}`, { method: 'POST' });
  const handleKeepPriority = (messageId) => apiAction(`/api/actions/keep-priority/${messageId}`, { method: 'POST' });
  const handleStarEmail = (messageId) => apiAction(`/api/actions/star-email/${messageId}`, { method: 'POST' });
  const handleUnstarEmail = (messageId) => apiAction(`/api/actions/unstar-email/${messageId}`, { method: 'POST' });
  const handleDeleteEmail = (messageId) => apiAction(`/api/actions/delete-email/${messageId}`, { method: 'POST' });
  const handleGetEmailContent = (messageId) => apiAction(`/api/actions/get-email-content/${messageId}`);
  const handleBulkUnstar = (messageIds) => apiAction('/api/actions/bulk-unstar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(messageIds) });
  const handleSendMessage = (message) => apiAction(`/api/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message }) });
  const handleTriggerCheck = () => apiAction('/api/trigger-check', { method: 'POST' });
  const handleStopCheck = () => apiAction('/api/stop-check', { method: 'POST' });
  const handleClearChat = () => apiAction('/api/chat/clear', { method: 'DELETE' });

  const handleComposeFromSuggestion = (text, email) => {
    if (!email) {
      toast.error("Could not find the original email to reply to.");
      return;
    }

    const command = `Draft a reply to the email from "${email.from}" about "${email.subject}" saying: "${text}"`;

    setActiveView('dashboard');

    handleSendMessage(command);

    toast.success("Instructing agent to draft reply...");
  };

  const confirmAction = (title, message, action) => {
    setModalState({
      isOpen: true,
      title,
      message,
      onConfirm: () => {
        action();
        setModalState({ isOpen: false, title: '', message: '', onConfirm: () => {} });
      }
    });
  };

  const handleBulkAction = (handler, items, successMessage, isSingleItemHandler = true) => {
    const itemArray = Array.from(items);
    
    const promise = isSingleItemHandler 
        ? Promise.all(itemArray.map(id => handler(id)))
        : handler(itemArray);

    promise.then(() => {
        setSelectedItems(new Set());
        toast.success(`${itemArray.length} ${successMessage}`);
    }).catch(err => {
        toast.error(`Bulk action failed: ${err.message}`);
    });
  };

  const handleBulkDismiss = () => confirmAction('Dismiss Selected Items?', `This will dismiss ${selectedItems.size} items.`, () => handleBulkAction(handleDismissPriority, selectedItems, 'items dismissed.'));
  const handleBulkKeep = () => handleBulkAction(handleKeepPriority, selectedItems, 'items acknowledged.');
  const handleBulkRejectDrafts = () => confirmAction('Reject Selected Drafts?', `This will reject ${selectedItems.size} drafts.`, () => handleBulkAction(handleRejectDraft, selectedItems, 'drafts rejected.'));
  const handleBulkApproveLearnings = () => handleBulkAction(handleApproveLearning, selectedItems, 'learnings approved.');
  const handleBulkRejectLearnings = () => confirmAction('Reject Selected Learnings?', `This will reject ${selectedItems.size} learning proposals.`, () => handleBulkAction(handleRejectLearning, selectedItems, 'learnings rejected.'));
  const handleBulkUnstarEmails = () => confirmAction('Unstar Selected Emails?', `This will unstar ${selectedItems.size} emails.`, () => handleBulkAction(handleBulkUnstar, selectedItems, 'emails unstarred.', false));


  const handleAddFact = async (fact) => {
    try {
        const newFact = await apiAction('/api/knowledge-base', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fact })
        });
        setKnowledgeBase(prev => [newFact, ...prev]);
        toast.success("Fact added to knowledge base!");
    } catch (error) {
        toast.error(`Failed to add fact: ${error.message}`);
    }
  };

  const handleDeleteFact = (factId) => {
    confirmAction('Delete Fact?', 'This will permanently remove the fact from the agent\'s knowledge base.', async () => {
        try {
            await apiAction(`/api/knowledge-base/${factId}`, { method: 'DELETE' });
            setKnowledgeBase(prev => prev.filter(f => f.id !== factId));
            toast.success("Fact deleted.");
        } catch (error) {
            toast.error(`Failed to delete fact: ${error.message}`);
        }
    });
  };
  
  const handleUpdateSettings = async (newSettings) => {
    try {
        await apiAction('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newSettings)
        });
        setSettings(newSettings);
        return true;
    } catch (error) {
        toast.error(`Failed to save settings: ${error.message}`);
        return false;
    }
  };

  const handleResetSettings = () => {
    confirmAction('Reset to Defaults?', 'All your saved settings will be reset to their original values. This cannot be undone.', async () => {
        try {
            const defaultSettings = await apiAction('/api/settings/reset', { method: 'POST' });
            setSettings(defaultSettings);
            toast.success("Settings have been reset to default.");
        } catch (error) {
            toast.error(`Failed to reset settings: ${error.message}`);
        }
    });
  };

  const handleClearKnowledgeBase = () => {
    confirmAction('Clear Knowledge Base?', 'This will permanently delete ALL learned facts from the agent\'s memory. This is irreversible.', async () => {
        try {
            await apiAction('/api/knowledge-base/all', { method: 'DELETE' });
            setKnowledgeBase([]);
            toast.success("Knowledge base has been cleared.");
        } catch (error) {
            toast.error(`Failed to clear knowledge base: ${error.message}`);
        }
    });
  };

  const renderActiveView = () => {
    switch(activeView) {
      case 'knowledge':
        return (
            <div className="flex-1 overflow-y-auto p-4 md:p-6 no-scrollbar">
                <KnowledgeBaseView 
                    knowledgeBase={knowledgeBase}
                    onAddFact={handleAddFact}
                    onDeleteFact={handleDeleteFact}
                />
            </div>
        );
      case 'settings':
        return (
            <div className="flex-1 overflow-y-auto p-4 md:p-6 no-scrollbar">
                <SettingsView 
                    settings={settings}
                    onUpdateSettings={handleUpdateSettings}
                    onResetSettings={handleResetSettings}
                    onClearKnowledgeBase={handleClearKnowledgeBase}
                />
            </div>
        );
      case 'label_view':
        return (
            <div className="flex-1 overflow-y-auto p-4 md:p-6 no-scrollbar">
                <LabelView 
                    label={selectedLabel}
                    apiAction={apiAction}
                    onStar={handleStarEmail}
                    onUnstar={handleUnstarEmail}
                    onDelete={(id) => confirmAction('Delete Email?', 'This will move the email to the trash.', () => handleDeleteEmail(id))}
                    sendMessage={sendMessage}
                    smartReplies={smartReplies}
                    onSelectSmartReply={handleComposeFromSuggestion}
                    clearSmartReplies={() => setSmartReplies([])}
                />
            </div>
        );
      case 'dashboard':
      default:
        return (
          <div className="flex-1 flex flex-col md:flex-row h-full overflow-hidden">
            <div className="flex flex-col flex-1 lg:w-2/3 p-4 md:p-6 space-y-6 overflow-y-auto no-scrollbar">
              <div className="flex-shrink-0" style={{ height: '40%' }}>
                <ActivityFeed activityFeed={activityFeed} />
              </div>
              <div className="flex-1 min-h-0">
                <ActionQueue
                    isLoading={isLoading}
                    drafts={drafts}
                    learningProposals={learningProposals}
                    priorityItems={priorityItems}
                    starredItems={starredItems}
                    selectedItems={selectedItems}
                    setSelectedItems={setSelectedItems}
                    confirmAction={confirmAction}
                    onBulkDismiss={handleBulkDismiss}
                    onBulkKeep={handleBulkKeep}
                    onBulkRejectDrafts={handleBulkRejectDrafts}
                    onBulkApproveLearnings={handleBulkApproveLearnings}
                    onBulkRejectLearnings={handleBulkRejectLearnings}
                    onBulkUnstar={handleBulkUnstarEmails}
                    handleSendDraft={handleSendDraft}
                    handleRejectDraft={handleRejectDraft}
                    handleApproveLearning={handleApproveLearning}
                    handleRejectLearning={handleRejectLearning}
                    handleDismissPriority={handleDismissPriority}
                    handleKeepPriority={handleKeepPriority}
                    handleStarEmail={handleStarEmail}
                    handleUnstarEmail={handleUnstarEmail}
                    handleGetEmailContent={handleGetEmailContent}
                    onContextualChat={setChatInput}
                />
              </div>
            </div>
            <div className="hidden lg:block lg:w-1/3 border-l border-gray-200 dark:border-gray-700">
              <ConversationalControl 
                chatHistory={chatHistory} 
                onSendMessage={handleSendMessage}
                chatInput={chatInput}
                setChatInput={setChatInput}
                onClearChat={() => confirmAction('Clear Chat History?', 'This will permanently delete the entire conversation. This action cannot be undone.', handleClearChat)}
              />
            </div>
          </div>
        );
    }
  };


  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (query) => {
    if (!query.trim()) {
      setSearchResults(null);
      return;
    }
    setSearchQuery(query);
    setIsSearching(true);
    try {
      const data = await apiAction('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      setSearchResults(data);
    } catch (error) {
      console.error("Search failed:", error);
      setSearchResults({ error: "Failed to fetch search results." });
    } finally {
      setIsSearching(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    setSearchResults(null);
  };

  return (
    <div className={`h-screen w-screen bg-gray-100 dark:bg-gray-900 flex font-sans transition-colors duration-300`}>
      <Toaster position="bottom-right" />
      <ConfirmationModal 
        isOpen={modalState.isOpen}
        onClose={() => setModalState({ isOpen: false, title: '', message: '', onConfirm: () => {} })}
        onConfirm={modalState.onConfirm}
        title={modalState.title}
        message={modalState.message}
      />
      <Sidebar 
        activeView={activeView} 
        setActiveView={setActiveView} 
        theme={theme} 
        toggleTheme={toggleTheme}
        labels={labels}
        selectedLabelId={selectedLabel ? selectedLabel.id : null}
        onLabelSelect={(label) => {
            setSelectedLabel(label);
            setActiveView('label_view');
        }}
      />
      <main className="flex-1 flex flex-col h-screen overflow-hidden">
        <Header 
            agentStatus={agentStatus} 
            onTriggerCheck={handleTriggerCheck}
            onStopCheck={handleStopCheck}
            onSearch={handleSearch}
            onClearSearch={clearSearch}
        />
        {searchResults ? (
          <div className="flex-1 overflow-y-auto p-4 md:p-6 no-scrollbar">
              <SearchResults
                  results={searchResults}
                  isLoading={isSearching}
                  onClear={clearSearch}
              />
          </div>
        ) : (
          renderActiveView()
        )}
      </main>
      <style>{`
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
      `}</style>
    </div>
  );
}

