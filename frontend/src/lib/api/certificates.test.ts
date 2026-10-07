import { describe, expect, it } from 'vitest';
import { certificatesForModel, type Certificate } from './certificateHelpers';

function cert(model: string, verification: Certificate['verification']): Certificate {
  return {
    id: `${model}-${verification}`,
    model_version: model,
    regulation_versions: [],
    proof_hash: 'abc',
    hmac_signature: 'sig',
    created_at: null,
    verification,
  };
}

describe('certificatesForModel', () => {
  it('returns only intact certificates for that model', () => {
    const all = [cert('v1', 'valid'), cert('v1', 'tampered'), cert('v2', 'valid')];
    expect(certificatesForModel(all, 'v1').map((c) => c.id)).toEqual(['v1-valid']);
  });
});
