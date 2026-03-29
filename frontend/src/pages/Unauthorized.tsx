import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

const Unauthorized: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6">
      <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-6">
        <ShieldAlert className="text-red-500 w-10 h-10" />
      </div>
      <h1 className="text-3xl font-bold text-white mb-2">Access Denied</h1>
      <p className="text-slate-400 text-center max-w-md mb-8">
        Your clearance level is insufficient for this sector. 
        Authentication logs have been dispatched to the Compliance Officer.
      </p>
      <Link 
        to="/" 
        className="flex items-center gap-2 px-6 py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-xl transition-all border border-slate-800"
      >
        <ArrowLeft size={18} />
        Return to Safety
      </Link>
    </div>
  );
};

export default Unauthorized;
