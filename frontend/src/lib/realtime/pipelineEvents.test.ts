import { describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/auth/supabase', () => ({ supabase: {} }));

import { mergeEvent, type PipelineEventRow } from './pipelineEvents';

function row(id: string, at: string): PipelineEventRow {
  return {
    id,
    stage: 'ci',
    gate_name: 'symbolic_check',
    status: 'compliant',
    model_version: 'v1',
    rule_ids: [],
    duration_ms: 1,
    plain_english_result: '',
    created_at: at,
  };
}

describe('mergeEvent', () => {
  it('puts the newest event first', () => {
    const merged = mergeEvent([row('a', '2026-10-07T10:00:00Z')], row('b', '2026-10-07T11:00:00Z'));
    expect(merged.map((e) => e.id)).toEqual(['b', 'a']);
  });

  it('ignores an event it already has', () => {
    const list = [row('a', '2026-10-07T10:00:00Z')];
    expect(mergeEvent(list, row('a', '2026-10-07T10:00:00Z'))).toBe(list);
  });

  it('keeps at most 100 events', () => {
    let list: PipelineEventRow[] = [];
    for (let i = 0; i < 120; i++) {
      list = mergeEvent(list, row(String(i), new Date(2026, 9, 7, 0, i).toISOString()));
    }
    expect(list).toHaveLength(100);
  });
});
