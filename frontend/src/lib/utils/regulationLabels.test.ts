import { describe, expect, it } from 'vitest';
import {
  regulationLabel,
  regulationVersionLabel,
  versionDate,
} from './regulationLabels';

describe('regulation labels', () => {
  it('turns a rule id into plain words', () => {
    expect(regulationLabel('RBI-4.1')).toBe('RBI section 4.1');
  });

  it('reads the date out of a version id', () => {
    expect(versionDate('RBI-4.1-20261007T120000Z')).toBe('7 Oct 2026');
    expect(versionDate('RBI-4.1')).toBeNull();
  });

  it('always shows the regulation version', () => {
    expect(regulationVersionLabel('RBI-4.1', 'RBI-4.1-20261007T120000Z')).toBe(
      'RBI section 4.1, version of 7 Oct 2026',
    );
    expect(regulationVersionLabel('RBI-4.1', 'weird')).toBe('RBI section 4.1');
  });
});
