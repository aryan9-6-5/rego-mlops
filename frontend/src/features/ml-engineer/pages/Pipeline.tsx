import React from 'react';

const Pipeline: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium text-white">Active Pipelines</h2>
        <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-sm font-medium">
          New Experiment
        </button>
      </div>
      
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-800/50 text-slate-400">
            <tr>
              <th className="px-6 py-4 font-medium uppercase tracking-wider">Pipeline ID</th>
              <th className="px-6 py-4 font-medium uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 font-medium uppercase tracking-wider">Compliance</th>
              <th className="px-6 py-4 font-medium uppercase tracking-wider">Last Sync</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {[1, 2].map((i) => (
              <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                <td className="px-6 py-4 text-white font-mono">PL-00{i}-REG</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 text-xs font-medium">
                    Running
                  </span>
                </td>
                <td className="px-6 py-4 text-slate-400 italic">Vetting required</td>
                <td className="px-6 py-4 text-slate-500">2 min ago</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Pipeline;
