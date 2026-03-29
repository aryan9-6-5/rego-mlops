import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuth } from './useAuth';
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
});
