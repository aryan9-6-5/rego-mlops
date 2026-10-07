import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api/client';
import type { Certificate } from './certificateHelpers';

const CERTIFICATES_KEY = ['certificates'] as const;

export function useCertificates() {
  return useQuery({
    queryKey: CERTIFICATES_KEY,
    queryFn: async () => (await api.get<Certificate[]>('/certificates/')).data,
  });
}

export function useDeployModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (modelVersion: string) =>
      (await api.post<{ model_version: string; certificate_id: string }>(
        '/pipeline/deploy',
        { model_version: modelVersion },
      )).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CERTIFICATES_KEY }),
  });
}

/** Save a certificate as a JSON file, for an auditor. */
export function downloadCertificate(certificate: Certificate): void {
  const { verification: _verification, ...data } = certificate;
  void _verification;
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `certificate-${certificate.model_version}.json`;
  link.click();
  URL.revokeObjectURL(url);
}
