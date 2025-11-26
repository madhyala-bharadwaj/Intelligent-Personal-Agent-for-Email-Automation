import React, { useState, useRef, useEffect } from 'react';
import { Bot, User, Send, Copy, Zap, Trash2, Sparkles } from 'lucide-react';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';

// --- CodeBlock Component (for Markdown rendering) ---
const CodeBlock = ({ node, inline, className, children, ...props }) => {
    const match = /language-(\w+)/.exec(className || '');
    const code = String(children).replace(/\n$/, '');
    
    const handleCopy = () => {
        const textArea = document.createElement('textarea');
        textArea.value = code;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            toast.success('Code copied!');
        } catch (err) {
            toast.error('Failed to copy.');
        }
        document.body.removeChild(textArea);
    };

    return !inline ? (
        <div className="bg-gray-800 dark:bg-black/50 rounded-lg my-2 shadow-inner">
            <div className="flex justify-between items-center px-4 py-1.5 bg-gray-700/50 dark:bg-black/20 rounded-t-lg">
                <span className="text-xs font-sans text-gray-400 select-none">{match ? match[1] : 'code'}</span>
                <button onClick={handleCopy} className="flex items-center gap-1.5 text-xs text-gray-300 hover:text-white transition-colors">
                    <Copy size={14} /> Copy
                </button>
            </div>
            <pre className="p-4 text-sm text-white overflow-x-auto">
                <code className={className} {...props}>{children}</code>
            </pre>
        </div>
    ) : (
        <code className="bg-gray-200 dark:bg-gray-600/50 px-1.5 py-1 rounded-md text-sm font-mono" {...props}>{children}</code>
    );
};

// --- ToolUseMessage Component ---
const ToolUseMessage = ({ toolName }) => (
    <div className="flex items-center justify-center gap-2 my-4 animate-fade-in">
        <div className="h-px flex-1 bg-gray-200 dark:bg-gray-700"></div>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
            <Zap size={14} className="text-yellow-500" />
            <span>Using <strong>{toolName}</strong>...</span>
        </div>
        <div className="h-px flex-1 bg-gray-200 dark:bg-gray-700"></div>
    </div>
);

// --- TypingIndicator Component ---
const TypingIndicator = () => (
    <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
            <Bot size={18} className="text-gray-600 dark:text-gray-300" />
        </div>
        <div className="mt-2 flex items-center gap-1.5">
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0s' }}></span>
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></span>
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></span>
        </div>
    </div>
);

// --- ChatMessage Component ---
const ChatMessage = ({ msg }) => {
    const isUser = msg.role === 'user';
    
    return (
        <div className={`flex items-start gap-3 ${isUser ? 'justify-end' : ''} animate-fade-in`}>
            {!isUser && (
                <div className="flex-shrink-0 w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
                    <Bot size={18} className="text-gray-600 dark:text-gray-300" />
                </div>
            )}
            <div className={`prose prose-sm dark:prose-invert max-w-[85%] p-3 px-4 rounded-2xl shadow-sm ${isUser ? 'bg-indigo-600 text-white rounded-br-lg' : 'bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-bl-lg border border-gray-200 dark:border-gray-600'}`}>
                <ReactMarkdown
                    children={msg.content}
                    components={{ code: CodeBlock }}
                />
            </div>
            {isUser && (
               <div className="flex-shrink-0 w-8 h-8 bg-gray-200 dark:bg-gray-600 rounded-full flex items-center justify-center">
                    <User size={18} className="text-gray-600 dark:text-gray-300" />
                </div>
            )}
        </div>
    );
};

// --- SuggestedPrompts Component ---
const SuggestedPrompts = ({ onPromptClick }) => {
    const prompts = [
        "Summarize my pending draft emails",
        "Check my availability for a meeting this week",
        "Draft a follow-up to the Wipro email",
        "Check for urgent tasks"
    ];

    return (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-4 animate-fade-in">
            <div className="w-16 h-16 bg-indigo-100 dark:bg-indigo-500/20 rounded-full flex items-center justify-center text-indigo-600 dark:text-indigo-300 mb-4">
                <Sparkles size={32} />
            </div>
            <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Agent Assistant</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">How can I help you today?</p>
            <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
                {prompts.map(prompt => (
                    <button 
                        key={prompt} 
                        onClick={() => onPromptClick(prompt)}
                        className="p-2 text-sm text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-500/10 rounded-lg hover:bg-indigo-100 dark:hover:bg-indigo-500/20 transition-colors"
                    >
                        {prompt}
                    </button>
                ))}
            </div>
        </div>
    );
};


const ConversationalControl = ({chatHistory, onSendMessage, chatInput, setChatInput, onClearChat }) => {
    const [isSending, setIsSending] = useState(false);
    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);

    const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });

    useEffect(scrollToBottom, [chatHistory, isSending]);

    // --- Auto-resize textarea ---
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            const scrollHeight = textareaRef.current.scrollHeight;
            textareaRef.current.style.height = `${scrollHeight}px`;
        }
    }, [chatInput]);

    const handleSendMessage = async (message) => {
        if (!message.trim() || isSending) return;
        setIsSending(true);
        try {
            await onSendMessage(message);
            setChatInput('');
        } catch (error) {
            toast.error("Failed to send message.");
        } finally {
            setIsSending(false);
        }
    };

    const handleFormSubmit = (e) => {
        e.preventDefault();
        handleSendMessage(chatInput);
    };
    
    const handlePromptClick = (prompt) => {
        setChatInput(prompt);
    }

    return (
        <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-800/90 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700/50">
            <div className="flex justify-between items-center p-3 border-b border-gray-200 dark:border-gray-700/50">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Agent Assistant</h2>
                <button 
                    onClick={onClearChat} 
                    className="p-2 text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 rounded-full hover:bg-red-100 dark:hover:bg-red-500/20 transition-colors"
                    title="Clear Chat History"
                >
                    <Trash2 size={16} />
                </button>
            </div>
            <div className="flex-1 p-4 overflow-y-auto text-sm space-y-5 no-scrollbar">
                {chatHistory.length === 0 && !isSending ? (
                    <SuggestedPrompts onPromptClick={handlePromptClick} />
                ) : (
                    chatHistory.map((msg, index) => {
                        if (msg.type === 'tool_use') {
                            return <ToolUseMessage key={index} toolName={msg.payload.tool_name} />;
                        }
                        if (msg.role === 'user' || msg.role === 'agent') {
                            return <ChatMessage key={index} msg={msg} />;
                        }
                        return null;
                    })
                )}
                {isSending && <TypingIndicator />}
                <div ref={messagesEndRef} />
            </div>

            <div className="p-3 border-t border-gray-200 dark:border-gray-700/50 bg-white dark:bg-gray-800 rounded-b-lg">
                <form onSubmit={handleFormSubmit} className="relative">
                    <textarea 
                        ref={textareaRef}
                        rows={1}
                        value={chatInput} 
                        onChange={(e) => setChatInput(e.target.value)} 
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleFormSubmit(e);
                            }
                        }}
                        placeholder="Ask the agent..." 
                        className="w-full pl-4 pr-12 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-800 dark:text-gray-200 focus:ring-2 focus:ring-indigo-500 transition-shadow resize-none max-h-40 no-scrollbar"
                    />
                    <button type="submit" disabled={isSending || !chatInput.trim()} className="absolute right-2 bottom-2 p-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-300 dark:disabled:bg-indigo-800 disabled:cursor-not-allowed transition-colors">
                        <Send size={18} />
                    </button>
                </form>
            </div>
            <style>{`
                .no-scrollbar::-webkit-scrollbar { display: none; } 
                .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
                @keyframes fade-in {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .animate-fade-in { animation: fade-in 0.3s ease-out forwards; }
            `}</style>
        </div>
    );
};

export default ConversationalControl;
