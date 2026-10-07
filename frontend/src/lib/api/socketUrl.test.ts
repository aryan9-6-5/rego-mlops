import { describe, expect, it } from 'vitest';
import { socketUrl } from './socketUrl';

describe('socketUrl', () => {
  it('turns an absolute http base into ws', () => {
    expect(socketUrl('http://localhost:8000/api', { protocol: 'http:', host: 'x' })).toBe(
      'ws://localhost:8000/api/pipeline/events',
    );
  });

  it('turns https into wss', () => {
    expect(socketUrl('https://rego.example/api', { protocol: 'https:', host: 'x' })).toBe(
      'wss://rego.example/api/pipeline/events',
    );
  });

  it('uses the page origin for a relative base, over wss on https pages', () => {
    expect(socketUrl('/api', { protocol: 'https:', host: 'rego.up.railway.app' })).toBe(
      'wss://rego.up.railway.app/api/pipeline/events',
    );
    expect(socketUrl('/api', { protocol: 'http:', host: 'localhost:8000' })).toBe(
      'ws://localhost:8000/api/pipeline/events',
    );
  });

  it('ignores a trailing slash', () => {
    expect(socketUrl('/api/', { protocol: 'http:', host: 'h' })).toBe('ws://h/api/pipeline/events');
  });
});
