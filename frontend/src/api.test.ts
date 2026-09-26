import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, filterTickets, parseIngest, request } from './api';
import type { Ticket } from './types';

const ticket: Ticket = {
  id: 't1',
  external_id: 'NS-101',
  title: 'Delayed delivery',
  body: 'The shipment has not arrived.',
  customer: 'Harbor Supply',
  priority: 'high',
  status: 'open',
  created_at: '2026-09-01T12:00:00Z',
};
const imported = {
  external_id: ticket.external_id,
  title: ticket.title,
  body: ticket.body,
  customer: ticket.customer,
  priority: ticket.priority,
};
afterEach(() => vi.unstubAllGlobals());

describe('workspace requests', () => {
  it('sends the current tenant key and JSON body to the relative API', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: 'a1', status: 'approved' }), { status: 200 }),
      );
    vi.stubGlobal('fetch', fetchMock);
    const result = await request('/actions/a1/approve', 'tenant-b-key', {
      method: 'POST',
      body: JSON.stringify({ decision: 'approve', note: 'Reviewed source.' }),
    });
    expect(result).toEqual({ id: 'a1', status: 'approved' });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/v1/actions/a1/approve');
    expect(options.headers.get('X-API-Key')).toBe('tenant-b-key');
    expect(options.headers.get('Content-Type')).toBe('application/json');
    expect(options.method).toBe('POST');
  });
  it('does not replace connectivity failures with demo data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Network error')));
    await expect(request('/tickets', 'key')).rejects.toMatchObject({
      status: 0,
      message: expect.stringContaining('Cannot reach RelayOps'),
    });
  });
  it('preserves cancellation so an old workspace cannot report a network failure', async () => {
    const abort = new DOMException('Aborted', 'AbortError');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(abort));
    await expect(request('/tickets', 'old-key')).rejects.toBe(abort);
  });
  it('explains invalid workspace credentials without disclosing the key', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 401 })));
    await expect(request('/workspace', 'secret-key')).rejects.toThrow(
      'This workspace key is not authorized.',
    );
  });
  it('reports a conflicting decision and keeps its HTTP status', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 409 })));
    await expect(request('/actions/a1/approve', 'key')).rejects.toMatchObject({
      status: 409,
      message: expect.stringContaining('already decided'),
    });
  });
  it('rejects HTML served at the API URL instead of pretending the workspace loaded', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('<!doctype html>', { status: 200 })),
    );
    await expect(request('/tickets', 'key')).rejects.toBeInstanceOf(ApiError);
  });
});

describe('ticket import validation', () => {
  it('accepts valid imported tickets without changing their external identifiers', () => {
    expect(parseIngest(JSON.stringify({ tickets: [imported] }))).toEqual({ tickets: [imported] });
  });
  it.each(['bad json', '[]', '{}', '{"tickets":[]}'])(
    'rejects malformed or empty batches: %s',
    (value) => {
      expect(() => parseIngest(value)).toThrow();
    },
  );
  it('rejects batches above the API limit', () => {
    expect(() =>
      parseIngest(JSON.stringify({ tickets: Array.from({ length: 101 }, () => imported) })),
    ).toThrow('100');
  });
  it('rejects oversized bodies and unrecognized priorities before sending them', () => {
    expect(() =>
      parseIngest(JSON.stringify({ tickets: [{ ...imported, body: 'a'.repeat(10001) }] })),
    ).toThrow('10,000');
    expect(() =>
      parseIngest(JSON.stringify({ tickets: [{ ...imported, priority: 'critical' }] })),
    ).toThrow('priority');
  });
  it('rejects blank identifiers needed for idempotent import', () => {
    expect(() =>
      parseIngest(JSON.stringify({ tickets: [{ ...imported, external_id: '  ' }] })),
    ).toThrow('external_id');
  });
});

describe('ticket queue filters', () => {
  const reviewed: Ticket = { ...ticket, id: 't2', external_id: 'NS-102', status: 'reviewed' };
  it('combines normalized text search with status rather than returning other statuses', () => {
    expect(filterTickets([ticket, reviewed], ' HARBOR ', 'reviewed')).toEqual([reviewed]);
  });
  it('finds an external ID and returns no fabricated result for a miss', () => {
    expect(filterTickets([ticket, reviewed], 'ns-101', 'all')).toEqual([ticket]);
    expect(filterTickets([ticket], 'missing customer', 'all')).toEqual([]);
  });
});
