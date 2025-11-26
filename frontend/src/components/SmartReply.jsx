import React from 'react';

/**
 * @param {object} props
 * @param {string[]} props.suggestions
 * @param {function(string): void} props.onSelectSuggestion
 */
const SmartReply = ({ suggestions, onSelectSuggestion }) => {
  // Don't render the component if there are no suggestions
  if (!suggestions || suggestions.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <h3 className="text-sm font-semibold mb-2 text-gray-600 dark:text-gray-300">
        Smart Replies
      </h3>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((text, index) => (
          <button
            key={index}
            onClick={() => onSelectSuggestion(text)}
            className="px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-100 hover:bg-blue-200 dark:bg-blue-900 dark:text-blue-200 dark:hover:bg-blue-800 rounded-full transition-colors duration-200 ease-in-out"
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SmartReply;
