import React from 'react';

const Regulations: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-slate-900/50 border border-slate-800 p-6 rounded-2xl animate-pulse">
            <div className="h-4 bg-slate-800 rounded w-3/4 mb-4"></div>
            <div className="h-3 bg-slate-800 rounded w-1/2 mb-2"></div>
            <div className="h-3 bg-slate-800 rounded w-5/6"></div>
          </div>
        ))}
      </div>
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8 text-center">
        <h2 className="text-xl font-medium text-white mb-2">Regulations Overview</h2>
        <p className="text-slate-400">Loading regulatory framework from Neo4j...</p>
      </div>
    </div>
  );
};

export default Regulations;
