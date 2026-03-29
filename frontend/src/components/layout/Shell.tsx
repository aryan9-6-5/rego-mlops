import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../lib/auth/useAuth';
import { 
  LayoutDashboard, 
  FileCheck, 
  GitBranch, 
  ShieldCheck, 
  LogOut, 
  User as UserIcon 
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ShellProps {
  children: React.ReactNode;
}

export const Shell: React.FC<ShellProps> = ({ children }) => {
  const { user, role, signOut } = useAuth();
  const location = useLocation();

  const navigation = [
    { 
      name: 'Overview', 
      href: '/', 
      icon: LayoutDashboard,
      roles: ['compliance_officer', 'ml_engineer']
    },
    { 
      name: 'Regulations', 
      href: '/regulations', 
      icon: FileCheck,
      roles: ['compliance_officer']
    },
    { 
      name: 'Pipeline', 
      href: '/pipeline', 
      icon: GitBranch,
      roles: ['ml_engineer']
    },
    { 
      name: 'Certificates', 
      href: '/certificates', 
      icon: ShieldCheck,
      roles: ['compliance_officer', 'ml_engineer']
    },
  ];

  const filteredNav = navigation.filter(item => 
    !role || item.roles.includes(role)
  );

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 bg-slate-900/50 flex flex-col">
        <div className="p-6 border-b border-slate-800 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/20">
            R
          </div>
          <span className="font-bold text-xl tracking-tight text-white italic">REGO</span>
        </div>

        <nav className="flex-1 p-4 space-y-2 mt-4">
          {filteredNav.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.href}
                to={item.href}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200",
                  "group relative overflow-hidden",
                  isActive 
                    ? "bg-blue-600/10 text-blue-400 font-medium" 
                    : "hover:bg-slate-800 text-slate-400 hover:text-slate-200"
                )}
              >
                {isActive && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500 rounded-full" />
                )}
                <Icon size={20} className={cn(
                  "transition-transform group-hover:scale-110",
                  isActive ? "text-blue-500" : "text-slate-500"
                )} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        {/* User Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/80">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 border border-slate-700">
              <UserIcon size={24} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">
                {user?.email?.split('@')[0] || 'User'}
              </p>
              <p className="text-xs text-slate-500 capitalize">{role?.replace('_', ' ')}</p>
            </div>
            <button 
              onClick={signOut}
              className="p-2 hover:bg-red-500/10 hover:text-red-500 text-slate-500 rounded-lg transition-colors"
              title="Sign Out"
            >
              <LogOut size={20} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <header className="h-16 border-b border-slate-800 flex items-center px-8 bg-slate-950/50 sticky top-0 backdrop-blur-md z-10">
          <h1 className="text-xl font-semibold text-white">
            {filteredNav.find(n => n.href === location.pathname)?.name || 'Page Not Found'}
          </h1>
        </header>
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  );
};
