import { describe, expect, it } from 'vitest';
import { MAX_REGULATORY_TEXT_CHARS } from '@/lib/utils/constants';
import { validateRegulationForm } from './validateRegulationForm';

describe('validateRegulationForm', () => {
  it('accepts a section and text', () => {
    expect(validateRegulationForm('4.1', 'Models shall not use PIN codes.')).toEqual({});
  });

  it('flags empty fields', () => {
    const errors = validateRegulationForm('  ', '   ');
    expect(errors.section).toBeDefined();
    expect(errors.content).toBeDefined();
  });

  it('flags text over the limit', () => {
    const errors = validateRegulationForm('4.1', 'x'.repeat(MAX_REGULATORY_TEXT_CHARS + 1));
    expect(errors.content).toContain('limit');
  });
});
