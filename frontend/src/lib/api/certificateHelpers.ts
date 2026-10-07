export interface CertificateRegulation {
  version_id: string;
  rule_id: string;
  formula_hash: string;
}

export interface Certificate {
  id: string;
  model_version: string;
  regulation_versions: CertificateRegulation[];
  proof_hash: string;
  hmac_signature: string;
  created_at: string | null;
  verification: 'valid' | 'tampered';
}

/** Intact certificates issued for one model version. */
export function certificatesForModel(
  certificates: Certificate[],
  modelVersion: string,
): Certificate[] {
  return certificates.filter(
    (c) => c.model_version === modelVersion && c.verification === 'valid',
  );
}
