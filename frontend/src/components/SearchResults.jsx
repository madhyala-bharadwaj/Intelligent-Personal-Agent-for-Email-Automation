import React from 'react';
import { Mail, Folder, BrainCircuit, Loader2, X } from 'lucide-react';

const SearchResultItem = ({ icon, title, subtitle, url }) => (
  <a
    href={url}
    target="_blank"
    rel="noopener noreferrer"
    className="block p-3 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
  >
    <div className="flex items-center gap-4">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700/50 flex items-center justify-center text-gray-500 dark:text-gray-400">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-gray-800 dark:text-gray-100 truncate">{title}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{subtitle}</p>
      </div>
    </div>
  </a>
);

const SearchResults = ({ results, isLoading, onClear }) => {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={32} className="animate-spin text-indigo-500" />
      </div>
    );
  }

  if (!results) {
    return null;
  }

  if (results.error) {
    return (
      <div className="p-6 text-center">
        <h3 className="text-lg font-semibold text-red-600 dark:text-red-400">Search Failed</h3>
        <p className="text-gray-600 dark:text-gray-400">{results.error}</p>
      </div>
    );
  }

  const hasResults =
    (results.emails?.length ?? 0) > 0 ||
    (results.drive_files?.length ?? 0) > 0 ||
    (results.knowledge_base?.length ?? 0) > 0;

  return (
    <div className="p-6 bg-white dark:bg-gray-800/50 rounded-xl shadow-sm h-full flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">Search Results</h2>
        <button
          onClick={onClear}
          className="p-2 text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-100 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          <X size={20} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {!hasResults ? (
          <p className="text-center text-gray-500 dark:text-gray-400 py-10">No results found.</p>
        ) : (
          <div className="space-y-6">
            {results.emails?.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Emails</h3>
                <div className="space-y-1">
                  {results.emails.map((email) => (
                    <SearchResultItem
                      key={email.id}
                      icon={<Mail size={16} />}
                      title={email.subject}
                      subtitle={`From: ${email.from}`}
                      url={`https://mail.google.com/mail/u/0/#inbox/${email.threadId}`}
                    />
                  ))}
                </div>
              </section>
            )}

            {results.drive_files?.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Drive Files</h3>
                <div className="space-y-1">
                  {results.drive_files.map((file) => (
                    <SearchResultItem
                      key={file.id}
                      icon={<Folder size={16} />}
                      title={file.name}
                      subtitle="Google Drive File"
                      url={file.webViewLink}
                    />
                  ))}
                </div>
              </section>
            )}

            {results.knowledge_base?.length > 0 && (
              <section>
                <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">Knowledge Base</h3>
                <div className="space-y-1">
                  {results.knowledge_base.map((fact, index) => (
                    <div key={index} className="p-3">
                      <div className="flex items-start gap-4">
                        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700/50 flex items-center justify-center text-gray-500 dark:text-gray-400">
                          <BrainCircuit size={16} />
                        </div>
                        <p className="text-sm text-gray-700 dark:text-gray-300 pt-1.5">{fact.fact || fact}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchResults;
