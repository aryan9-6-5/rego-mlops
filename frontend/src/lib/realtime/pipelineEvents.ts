import { useEffect } from 'react';
import { create } from 'zustand';
import { supabase } from '@/lib/auth/supabase';

export interface PipelineEventRow {
  id: string;
  stage: string;
  gate_name: string;
  status: string;
  model_version: string;
  rule_ids: string[];
  duration_ms: number;
  plain_english_result: string;
  created_at: string;
}

const MAX_EVENTS = 100;
const INITIAL_LIMIT = 50;

interface EventsState {
  events: PipelineEventRow[]; // newest first
  loaded: boolean;
  error: string | null;
  live: boolean;
  setEvents: (events: PipelineEventRow[]) => void;
  addEvent: (event: PipelineEventRow) => void;
  setError: (message: string | null) => void;
  setLive: (live: boolean) => void;
}

export function mergeEvent(
  events: PipelineEventRow[],
  event: PipelineEventRow,
): PipelineEventRow[] {
  if (events.some((e) => e.id === event.id)) return events;
  return [event, ...events]
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
    .slice(0, MAX_EVENTS);
}

export const usePipelineEventsStore = create<EventsState>((set) => ({
  events: [],
  loaded: false,
  error: null,
  live: false,
  setEvents: (events) => set({ events, loaded: true, error: null }),
  addEvent: (event) => set((s) => ({ events: mergeEvent(s.events, event) })),
  setError: (error) => set({ error, loaded: true }),
  setLive: (live) => set({ live }),
}));

/** Loads recent CI gate events, then streams new ones with Supabase Realtime.
 * Dashboards read the store, so a new violation shows up with no page refresh. */
export function usePipelineEventsFeed(): void {
  useEffect(() => {
    const store = usePipelineEventsStore.getState();
    let active = true;

    void supabase
      .from('pipeline_events')
      .select('*')
      .eq('stage', 'ci')
      .order('created_at', { ascending: false })
      .limit(INITIAL_LIMIT)
      .then(({ data, error }) => {
        if (!active) return;
        if (error) store.setError('Could not load recent checks.');
        else store.setEvents((data ?? []) as PipelineEventRow[]);
      });

    const channel = supabase
      .channel('pipeline-events')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'pipeline_events' },
        (payload) => store.addEvent(payload.new as PipelineEventRow),
      )
      .subscribe((status) => store.setLive(status === 'SUBSCRIBED'));

    return () => {
      active = false;
      store.setLive(false);
      void supabase.removeChannel(channel);
    };
  }, []);
}
