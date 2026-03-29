import { create } from 'zustand';
import { supabase } from './supabase';
import { User } from '@supabase/supabase-js';

interface AuthState {
  user: User | null;
  role: string | null;
  loading: boolean;
  initialized: boolean;
  setUser: (user: User | null) => void;
  setRole: (role: string | null) => void;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  role: null,
  loading: true,
  initialized: false,
  setUser: (user) => set({ user }),
  setRole: (role) => set({ role }),
  signOut: async () => {
    await supabase.auth.signOut();
    set({ user: null, role: null });
  },
  refreshSession: async () => {
    const { data: { session } } = await supabase.auth.getSession();
    if (session) {
      set({ user: session.user, loading: true });
      // Fetch role from profile table
      const { data, error } = await supabase
        .from('users')
        .select('role')
        .eq('id', session.user.id)
        .single();
      
      if (!error && data) {
        set({ role: data.role });
      }
    }
    set({ loading: false, initialized: true });
  },
}));

// Initialize listener
supabase.auth.onAuthStateChange(async (_event, session) => {
  const store = useAuth.getState();
  if (session) {
    store.setUser(session.user);
    const { data } = await supabase
      .from('users')
      .select('role')
      .eq('id', session.user.id)
      .single();
    if (data) store.setRole(data.role);
  } else {
    store.setUser(null);
    store.setRole(null);
  }
  useAuth.setState({ loading: false, initialized: true });
});
