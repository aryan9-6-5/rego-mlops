import React from 'react';
import { 
  ShieldAlert, 
  CheckCircle2, 
  Activity, 
  Clock 
} from 'lucide-react';

const Dashboard: React.FC = () => {

  const stats = [
    { name: 'Active Regulations', value: '12', icon: ShieldAlert, color: 'text-orange-500' },
    { name: 'Verified Pipelines', value: '4', icon: CheckCircle2, color: 'text-green-500' },
    { name: 'System Integrity', value: '99.9%', icon: Activity, color: 'text-blue-500' },
    { name: 'Last Proof Generation', value: '14m ago', icon: Clock, color: 'text-purple-500' },
  ];

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div key={stat.name} className="bg-slate-900/40 border border-slate-800 p-6 rounded-2xl hover:bg-slate-900/60 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <stat.icon className={stat.color} size={24} />
              <span className="text-xs font-mono text-slate-500">REALTIME</span>
            </div>
            <p className="text-2xl font-bold text-white mb-1">{stat.value}</p>
            <p className="text-sm text-slate-400 font-medium">{stat.name}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6">
          <h3 className="text-white font-semibold mb-6">Security Graph Status</h3>
          <div className="h-64 flex items-end justify-between gap-2 px-4">
            {[40, 70, 45, 90, 65, 80, 50, 85, 95].map((h, i) => (
              <div 
                key={i} 
                className="w-full bg-blue-600/20 rounded-t-md hover:bg-blue-600/40 transition-all cursor-pointer group relative"
                style={{ height: `${h}%` }}
              >
                <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-slate-800 text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                  {h}%
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex justify-between text-[10px] text-slate-500 uppercase tracking-widest font-mono">
            <span>00:00</span>
            <span>06:00</span>
            <span>12:00</span>
            <span>18:00</span>
          </div>
        </div>

        <div className="bg-slate-900/40 border border-slate-800 rounded-2xl p-6">
          <h3 className="text-white font-semibold mb-6">Recent Activity</h3>
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex gap-4 p-3 rounded-xl hover:bg-slate-800/20 transition-colors border border-transparent hover:border-slate-800/50">
                <div className="w-2 h-2 rounded-full bg-blue-500 mt-2" />
                <div>
                  <p className="text-sm text-slate-200">Z3 proof generated for pipeline <span className="text-blue-400 font-mono">PL-882</span></p>
                  <p className="text-xs text-slate-500 mt-1">2 mins ago • ML Engineer</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
