import { describe, it, expect, vi, beforeEach } from 'vitest';
import { handleAuthChange, useAuth } from './useAuth';
import { supabase } from './supabase';

vi.mock('./supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
      signOut: vi.fn(),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } })),
    },
    from: vi.fn(() => ({
      select: vi.fn(() => ({
        eq: vi.fn(() => ({
          single: vi.fn(),
        })),
      })),
    })),
  },
}));

describe('useAuth hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.setState({ user: null, role: null, loading: false, initialized: false });
  });

  it('should initialize with default state', () => {
    const state = useAuth.getState();
    expect(state.user).toBeNull();
    expect(state.role).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.initialized).toBe(false);
  });

  it('should sign out and clear state', async () => {
    useAuth.setState({ user: { id: '123' } as never, role: 'ml_engineer' });
    
    await useAuth.getState().signOut();
    
    expect(supabase.auth.signOut).toHaveBeenCalled();
    const state = useAuth.getState();
    expect(state.user).toBeNull();
    expect(state.role).toBeNull();
  });

  it('should refresh session and fetch role', async () => {
    const mockUser = { id: '123', email: 'test@example.com' };
    const mockSession = { user: mockUser };
    
    vi.mocked(supabase.auth.getSession).mockResolvedValue({ 
      data: { session: mockSession as never }, 
      error: null 
    } as never);

    vi.mocked(supabase.from).mockReturnValue({
      select: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      single: vi.fn().mockResolvedValue({ 
        data: { role: 'compliance_officer' }, 
        error: null 
      }),
    } as never);

    await useAuth.getState().refreshSession();

    const state = useAuth.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.role).toBe('compliance_officer');
    expect(state.loading).toBe(false);
  });

  describe('handleAuthChange', () => {
    const session = { user: { id: 'u1' } } as never;

    function stubRole(role: string | null) {
      const single = vi.fn().mockResolvedValue({ data: role ? { role } : null, error: null });
      const eq = vi.fn(() => ({ single }));
      const select = vi.fn(() => ({ eq }));
      vi.mocked(supabase.from).mockReturnValue({ select } as never);
      return single;
    }

    it('does not query Supabase inside the callback, which would deadlock supabase-js', () => {
      const single = stubRole('compliance_officer');
      handleAuthChange(session);
      expect(supabase.from).not.toHaveBeenCalled();
      expect(single).not.toHaveBeenCalled();
      expect(useAuth.getState().user).toEqual({ id: 'u1' });
    });

    it('loads the role on a later tick and then marks auth ready', async () => {
      stubRole('compliance_officer');
      handleAuthChange(session);
      await vi.waitFor(() => expect(useAuth.getState().role).toBe('compliance_officer'));
      expect(useAuth.getState()).toMatchObject({ loading: false, initialized: true });
    });

    it('still becomes ready when the role lookup fails', async () => {
      const single = vi.fn().mockRejectedValue(new Error('offline'));
      vi.mocked(supabase.from).mockReturnValue({
        select: () => ({ eq: () => ({ single }) }),
      } as never);
      handleAuthChange(session);
      await vi.waitFor(() => expect(useAuth.getState().initialized).toBe(true));
      expect(useAuth.getState().role).toBeNull();
    });

    it('clears the user and role on sign-out', () => {
      useAuth.setState({ user: { id: 'u1' } as never, role: 'cto' });
      handleAuthChange(null);
      expect(useAuth.getState()).toMatchObject({
        user: null,
        role: null,
        loading: false,
        initialized: true,
      });
    });
  });
});
