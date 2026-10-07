import { create } from 'zustand';
import { supabase } from './supabase';
import type { Session, User } from '@supabase/supabase-js';

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

/** React to a sign-in or sign-out.
 *
 * Do not call Supabase from inside the `onAuthStateChange` callback and wait for
 * it: supabase-js waits for every callback before `getSession()` can answer, and
 * a query needs `getSession()` for its token, so the two wait on each other for
 * good. A signed-in user reloading the page would stay on "Authenticating..."
 * forever. The role lookup is deferred to a later tick instead.
 */
export function handleAuthChange(session: Session | null): void {
  const store = useAuth.getState();
  if (!session) {
    store.setUser(null);
    store.setRole(null);
    useAuth.setState({ loading: false, initialized: true });
    return;
  }
  store.setUser(session.user);
  setTimeout(() => {
    void supabase
      .from('users')
      .select('role')
      .eq('id', session.user.id)
      .single()
      .then(({ data }) => {
        if (data) useAuth.getState().setRole(data.role);
      })
      .then(
        () => useAuth.setState({ loading: false, initialized: true }),
        () => useAuth.setState({ loading: false, initialized: true }),
      );
  }, 0);
}

supabase.auth.onAuthStateChange((_event, session) => handleAuthChange(session));
