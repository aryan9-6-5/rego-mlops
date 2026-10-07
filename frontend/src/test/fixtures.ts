import type { Certificate } from '@/lib/api/certificateHelpers';
import type { Regulation } from '@/features/compliance-officer/api/regulations';

export function makeRegulation(overrides: Partial<Regulation> = {}): Regulation {
  return {
    id: 'reg-1',
    rule_id: 'RBI-4.1',
    jurisdiction: 'India',
    source_text: 'Lending models shall not use PIN codes.',
    description: 'Models must not use PIN codes.',
    formal_logic: '(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))',
    status: 'pending_approval',
    version: '20261007T120000000001Z',
    validation_message: null,
    ...overrides,
  };
}

export function makeCertificate(overrides: Partial<Certificate> = {}): Certificate {
  return {
    id: 'cert-1',
    model_version: 'v2.1.4',
    regulation_versions: [
      {
        version_id: 'RBI-4.1-20261007T120000000001Z',
        rule_id: 'RBI-4.1',
        formula_hash: 'f'.repeat(64),
      },
    ],
    proof_hash: 'a1b2c3'.repeat(10) + 'abcd',
    hmac_signature: 'sig',
    created_at: '2026-10-07T12:00:00Z',
    verification: 'valid',
    ...overrides,
  };
}
