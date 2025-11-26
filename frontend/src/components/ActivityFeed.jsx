import React from 'react';
import { Info, CheckCircle, AlertTriangle } from 'lucide-react';

const ActivityFeed = ({ activityFeed }) => {
  const getIcon = (type) => {
    switch (type) {
      case 'success':
        return <CheckCircle size={14} className="text-green-500" />;
      case 'error':
        return <AlertTriangle size={14} className="text-red-500" />;
      default:
        return <Info size={14} className="text-blue-500" />;
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-sm h-full flex flex-col">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex-shrink-0">Activity Feed</h2>
      <div className="flex-1 overflow-y-auto no-scrollbar">
        {activityFeed.length > 0 ? (
          <div className="space-y-4">
            {activityFeed.map((item, index) => (
              <div key={index} className="flex items-start gap-3">
                <div className="flex-shrink-0 w-6 h-6 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mt-0.5">
                  {getIcon(item.type)}
                </div>
                <div className="flex-1">
                  <p className="text-sm text-gray-700 dark:text-gray-300">{item.message}</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">{item.time}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-gray-500 dark:text-gray-400">The agent is idle. Press 'Check Emails' to begin processing</p>
          </div>
        )}
      </div>
      <style>{`
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
      `}</style>
    </div>
  );
};

export default ActivityFeed;
