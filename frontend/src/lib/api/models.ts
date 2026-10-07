import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';

export interface RegulationVersionRef {
  version_id: string;
  rule_id: string;
  section: string | null;
  status: string;
  activated_at: string | null;
  superseded_at: string | null;
  certified_at: string | null;
}

export interface ModelLineage {
  model_version: string;
  created_at: string | null;
  regulation_versions: RegulationVersionRef[];
}

export function useModelLineages() {
  return useQuery({
    queryKey: ['model-lineages'],
    queryFn: async () => (await api.get<ModelLineage[]>('/models/')).data,
  });
}

export function formatDate(iso: string | null): string {
  if (!iso) return 'Unknown date';
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}
