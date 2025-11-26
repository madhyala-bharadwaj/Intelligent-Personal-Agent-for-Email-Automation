import React, { useState, useMemo, useEffect } from 'react';
import { BrainCircuit, Plus, Search, Trash2, Save, Info, RotateCcw, Check, Loader2 } from 'lucide-react';

const Tooltip = ({ text, children }) => (
    <div className="relative inline-flex group">
        {children}
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2 bg-gray-800 text-white text-xs rounded-lg shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-10 pointer-events-none">
            {text}
        </div>
    </div>
);

const SettingsSection = ({ title, description, children, isDangerZone = false }) => (
    <div className={`grid grid-cols-1 md:grid-cols-3 gap-x-8 gap-y-6 py-8 border-b border-gray-200 dark:border-gray-700 ${isDangerZone ? 'border-red-500/30' : ''}`}>
        <div className="md:col-span-1">
            <h3 className={`text-lg font-semibold ${isDangerZone ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-gray-100'}`}>{title}</h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{description}</p>
        </div>
        <div className={`md:col-span-2 space-y-6 ${isDangerZone ? 'p-6 rounded-xl border border-red-500/30 bg-red-50 dark:bg-red-500/5' : ''}`}>
            {children}
        </div>
    </div>
);

const SettingInput = ({ label, id, type = "text", value, onChange, children, ...props }) => (
    <div>
        <label htmlFor={id} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">{label}</label>
        {children || (
            <input
                type={type}
                id={id}
                name={id}
                value={value}
                onChange={onChange}
                className="block w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition"
                {...props}
            />
        )}
    </div>
);

// --- Toggle Switch Component ---
const ToggleSwitch = ({ id, name, checked, onChange, label }) => (
    <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{label}</span>
        <label htmlFor={id} className="inline-flex relative items-center cursor-pointer">
            <input type="checkbox" id={id} name={name} checked={checked} onChange={onChange} className="sr-only peer" />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-indigo-600"></div>
        </label>
    </div>
);


export const SettingsView = ({ settings, onUpdateSettings, onResetSettings, onClearKnowledgeBase }) => {
    const [localSettings, setLocalSettings] = useState(settings);
    const [saveStatus, setSaveStatus] = useState('idle'); // idle, saving, saved

    useEffect(() => {
        setLocalSettings(settings);
    }, [settings]);

    if (!localSettings) {
        return (
            <div className="p-6 bg-white dark:bg-gray-800/50 rounded-xl shadow-sm h-full flex items-center justify-center">
                <p className="text-gray-500">Loading settings...</p>
            </div>
        );
    }

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        const val = type === 'checkbox' ? checked : type === 'number' ? parseFloat(value) : value;
        setLocalSettings(prev => ({ ...prev, [name]: val }));
    };

    const handleNestedChange = (e) => {
        const { name, checked } = e.target;
        setLocalSettings(prev => ({
            ...prev,
            notification_triggers: {
                ...prev.notification_triggers,
                [name]: checked
            }
        }));
    };

    const handleSave = async () => {
        setSaveStatus('saving');
        const success = await onUpdateSettings(localSettings);
        if (success) {
            setSaveStatus('saved');
            setTimeout(() => setSaveStatus('idle'), 2000);
        } else {
            setSaveStatus('idle');
        }
    };

    return (
        <div className="bg-white dark:bg-gray-800/50 rounded-xl shadow-sm h-full flex flex-col">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
                    <p className="mt-1 text-gray-600 dark:text-gray-400">Customize the agent's behavior and preferences.</p>
                </div>
                <div className="flex items-center gap-3">
                    <button onClick={onResetSettings} className="px-4 py-2 text-sm font-semibold text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600 flex items-center gap-2">
                        <RotateCcw size={16} /> Reset
                    </button>
                    <button onClick={handleSave} disabled={saveStatus === 'saving'} className={`px-4 py-2 text-sm font-semibold text-white rounded-lg flex items-center gap-2 shadow-sm transition-colors ${saveStatus === 'saving' ? 'bg-indigo-400' : saveStatus === 'saved' ? 'bg-green-500' : 'bg-indigo-600 hover:bg-indigo-700'}`}>
                        {saveStatus === 'saving' && <Loader2 size={16} className="animate-spin" />}
                        {saveStatus === 'saved' && <Check size={16} />}
                        {saveStatus === 'idle' && <Save size={16} />}
                        {saveStatus === 'saving' ? 'Saving...' : saveStatus === 'saved' ? 'Saved!' : 'Save Changes'}
                    </button>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto px-6 no-scrollbar pb-6">
                <SettingsSection title="General Behavior" description="Control the agent's core operational loop and startup behavior.">
                    <ToggleSwitch id="start_on_launch" name="start_on_launch" checked={localSettings.start_on_launch} onChange={handleChange} label="Start Agent on Launch" />
                    <SettingInput id="check_interval_seconds" type="number" value={localSettings.check_interval_seconds} onChange={handleChange} min="10" label={
                        <div className="flex items-center gap-2">
                            Processing Interval (seconds)
                            <Tooltip text="How often the agent checks for new emails. Lower values are faster but use more resources."><Info size={14} className="text-gray-400" /></Tooltip>
                        </div>
                    }/>
                </SettingsSection>

                <SettingsSection title="AI & Language" description="Configure the language model and how it generates responses.">
                    <SettingInput id="llm_model_name" label="AI Model">
                        <select id="llm_model_name" name="llm_model_name" value={localSettings.llm_model_name} onChange={handleChange} className="block w-full pl-4 pr-10 py-2 font-mono text-sm text-indigo-800 bg-indigo-50 border-indigo-200 dark:bg-indigo-500/10 dark:text-indigo-300 dark:border-indigo-500/30 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 transition">
                            <option>gemini-2.5-flash</option>
                            <option>gemini-2.5-flash-lite</option>
                            <option>gemini-2.0-flash</option>
                            <option>gemini-2.0-flash-lite</option>
                            <option>gemma-3-27b-it</option>
                            <option>gemma-3-12b-it</option>
                        </select>
                    </SettingInput>
                    <SettingInput id="llm_temperature" label={
                        <div className="flex items-center gap-2">Creativity (Temperature)<Tooltip text="Lower values are more factual; higher values are more creative."><Info size={14} className="text-gray-400" /></Tooltip></div>
                    }>
                        <div className="flex items-center gap-4">
                            <input type="range" id="llm_temperature" name="llm_temperature" min="0" max="1" step="0.1" value={localSettings.llm_temperature} onChange={handleChange} className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-600" />
                            <span className="font-mono text-sm text-gray-600 dark:text-gray-400 w-8 text-center bg-gray-100 dark:bg-gray-700/50 py-1 rounded-md">{localSettings.llm_temperature}</span>
                        </div>
                    </SettingInput>
                    <SettingInput id="default_email_signature" label="Default Email Signature">
                        <textarea id="default_email_signature" name="default_email_signature" value={localSettings.default_email_signature} onChange={handleChange} rows="3" className="block w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 sm:text-sm transition"></textarea>
                    </SettingInput>
                </SettingsSection>

                {/* --- Added Notifications Section --- */}
                <SettingsSection title="Notifications" description="Choose which real-time events you want to be notified about in the UI.">
                    <div className="space-y-4">
                        <ToggleSwitch id="new_draft" name="new_draft" checked={localSettings.notification_triggers.new_draft} onChange={handleNestedChange} label="New Draft Created" />
                        <ToggleSwitch id="priority_item" name="priority_item" checked={localSettings.notification_triggers.priority_item} onChange={handleNestedChange} label="High-Priority Item Detected" />
                        <ToggleSwitch id="new_learning" name="new_learning" checked={localSettings.notification_triggers.new_learning} onChange={handleNestedChange} label="New Fact Learned" />
                    </div>
                </SettingsSection>
                
                {/* --- Data Management Section --- */}
                <SettingsSection title="Data & Storage" description="Manage how the agent stores and retains information.">
                    <SettingInput id="drive_folder_name" label="Google Drive Folder Name" value={localSettings.drive_folder_name} onChange={handleChange} />
                    <SettingInput id="conversation_memory_retention_days" label="Conversation Memory Retention">
                        <select id="conversation_memory_retention_days" name="conversation_memory_retention_days" value={localSettings.conversation_memory_retention_days} onChange={handleChange} className="block w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 sm:text-sm transition">
                            <option value="90">90 Days</option>
                            <option value="30">30 Days</option>
                            <option value="7">7 Days</option>
                            <option value="-1">Forever</option>
                        </select>
                    </SettingInput>
                </SettingsSection>

                <SettingsSection title="Danger Zone" description="These actions are irreversible. Please be certain before proceeding." isDangerZone={true}>
                    <div className="flex justify-between items-center">
                        <div>
                            <h4 className="font-semibold text-gray-800 dark:text-gray-200">Clear Knowledge Base</h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400">Permanently delete all learned facts.</p>
                        </div>
                        <button onClick={onClearKnowledgeBase} className="px-4 py-2 text-sm font-semibold text-white bg-red-600 rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500">Clear Knowledge Base</button>
                    </div>
                </SettingsSection>
            </div>
        </div>
    );
};

export const KnowledgeBaseView = ({ knowledgeBase, onAddFact, onDeleteFact }) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [newFact, setNewFact] = useState('');
    const [isAdding, setIsAdding] = useState(false);

    const filteredFacts = useMemo(() => {
        if (!knowledgeBase) return [];
        const lowercasedQuery = searchQuery.toLowerCase();
        if (!lowercasedQuery) return knowledgeBase;
        return knowledgeBase.filter(item => 
            item.fact.toLowerCase().includes(lowercasedQuery)
        );
    }, [searchQuery, knowledgeBase]);

    const handleAddSubmit = (e) => {
        e.preventDefault();
        if (!newFact.trim()) return;
        onAddFact(newFact);
        setNewFact('');
        setIsAdding(false);
    };

    return (
        <div className="p-6 bg-white dark:bg-gray-800/50 rounded-xl shadow-sm h-full flex flex-col">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100">Knowledge Base</h1>
                    <p className="mt-1 text-gray-600 dark:text-gray-400">Manage the facts and information the agent uses for responses.</p>
                </div>
                <button onClick={() => setIsAdding(!isAdding)} className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800 flex items-center gap-2">
                    <Plus size={16} /> Add Fact
                </button>
            </div>
            {isAdding && (
                <form onSubmit={handleAddSubmit} className="mb-6 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                    <textarea value={newFact} onChange={(e) => setNewFact(e.target.value)} placeholder="Enter a new fact..." className="w-full p-2 text-sm border rounded-md bg-white dark:bg-gray-700 dark:text-gray-200 dark:border-gray-600 focus:ring-2 focus:ring-indigo-500" rows={3} />
                    <div className="flex justify-end gap-3 mt-3">
                        <button type="button" onClick={() => setIsAdding(false)} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600">Cancel</button>
                        <button type="submit" className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700">Save Fact</button>
                    </div>
                </form>
            )}
            <div className="relative mb-4">
                <input type="text" placeholder="Search knowledge base..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full pl-10 pr-4 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500" />
                <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/>
            </div>
            <div className="flex-1 overflow-y-auto pr-2 -mr-2">
                {filteredFacts.length > 0 ? (
                    <div className="space-y-3">
                        {filteredFacts.map(item => (
                            <div key={item.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg">
                                <p className="text-sm text-gray-800 dark:text-gray-200">{item.fact}</p>
                                <button onClick={() => onDeleteFact(item.id)} className="p-1.5 text-gray-400 hover:text-red-500 dark:hover:text-red-400 rounded-md hover:bg-red-100 dark:hover:bg-red-500/10">
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-12">
                        <div className="mx-auto w-16 h-16 bg-gray-100 dark:bg-gray-700/50 rounded-full flex items-center justify-center text-gray-400 dark:text-gray-500">
                            <BrainCircuit size={32} />
                        </div>
                        <h3 className="mt-4 text-lg font-semibold text-gray-800 dark:text-gray-100">{searchQuery ? "No Results Found" : "Knowledge Base is Empty"}</h3>
                        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{searchQuery ? "Try a different search term." : "Add a fact to get started."}</p>
                    </div>
                )}
            </div>
        </div>
    );
};
