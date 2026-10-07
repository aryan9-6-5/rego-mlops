import { describe, expect, it } from 'vitest';
import { readableRule } from './readableRule';

describe('readableRule', () => {
  it('reads a prohibition', () => {
    expect(
      readableRule('(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))'),
    ).toBe('The weight of pin code equals 0.');
  });

  it('reads comparisons, rationals and conjunctions', () => {
    expect(
      readableRule(
        '(declare-const income_weight Real)(assert (and (> income_weight 0) (<= income_weight (/ 1 2))))',
      ),
    ).toBe('(the weight of income is greater than 0) and (the weight of income is at most 0.5).');
  });

  it('reads negation and implication', () => {
    expect(readableRule('(assert (not (= a_weight 1)))')).toBe(
      'It is not true that the weight of a equals 1.',
    );
    expect(readableRule('(assert (=> (> a_weight 0) (= b_weight 0)))')).toBe(
      'If the weight of a is greater than 0, then the weight of b equals 0.',
    );
  });

  it('refuses what it cannot express instead of showing raw logic', () => {
    expect(readableRule('(assert (forall ((x Int)) (> x 0)))')).toBeNull();
    expect(readableRule('(assert (= a_weight')).toBeNull();
    expect(readableRule('')).toBeNull();
  });
});
