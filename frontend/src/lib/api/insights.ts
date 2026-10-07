import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';

export interface DriftEntry {
  version_id: string;
  rule_id: string;
  section: string | null;
  status: string;
  activated_at: string | null;
  superseded_at: string | null;
}

export interface FeatureChange {
  feature: string;
  kind: 'added' | 'removed' | 'changed';
  before: number | null;
  after: number | null;
  affects_rules: string[];
}

export interface ModelDiff {
  from_version: string;
  to_version: string;
  changes: FeatureChange[];
}

export function useDriftLog() {
  return useQuery({
    queryKey: ['drift-log'],
    queryFn: async () => (await api.get<DriftEntry[]>('/pipeline/drift-log')).data,
  });
}

export function useModelDiff(fromVersion: string, toVersion: string) {
  return useQuery({
    queryKey: ['model-diff', fromVersion, toVersion],
    enabled: fromVersion !== '' && toVersion !== '',
    retry: false,
    queryFn: async () =>
      (await api.get<ModelDiff>('/models/diff', {
        params: { from_version: fromVersion, to_version: toVersion },
      })).data,
  });
}
