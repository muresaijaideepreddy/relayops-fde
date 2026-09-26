import type { ImportedTicket, Ticket } from './types';

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function request<T>(
  path: string,
  apiKey: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('X-API-Key', apiKey);
  if (options.body) headers.set('Content-Type', 'application/json');
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { ...options, headers });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new ApiError('Cannot reach RelayOps. Start the backend on port 8000, then try again.', 0);
  }
  if (!response.ok) {
    let detail: unknown;
    try {
      detail = (await response.json()).detail;
    } catch {
      /* Non-JSON server response. */
    }
    const message =
      response.status === 401 || response.status === 403
        ? 'This workspace key is not authorized. Switch workspace or enter a valid key.'
        : typeof detail === 'string'
          ? detail
          : response.status === 409
            ? 'This action was already decided. Refresh to see its current status.'
            : `The request could not be completed (${response.status}). Please try again.`;
    throw new ApiError(message, response.status);
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(
      'The backend returned an unreadable response. Check that the API is running on port 8000.',
      response.status,
    );
  }
}

export function filterTickets(tickets: Ticket[], query: string, status: string): Ticket[] {
  const needle = query.trim().toLocaleLowerCase();
  return tickets.filter(
    (ticket) =>
      (status === 'all' || ticket.status === status) &&
      `${ticket.title} ${ticket.external_id} ${ticket.customer} ${ticket.body}`
        .toLocaleLowerCase()
        .includes(needle),
  );
}

export function parseIngest(value: string): { tickets: ImportedTicket[] } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new Error('Enter valid JSON containing a tickets array.');
  }
  if (
    !parsed ||
    typeof parsed !== 'object' ||
    !('tickets' in parsed) ||
    !Array.isArray(parsed.tickets)
  )
    throw new Error('Use an object with a tickets array, for example: { "tickets": [...] }.');
  if (!parsed.tickets.length || parsed.tickets.length > 100)
    throw new Error('Import between 1 and 100 tickets at a time.');
  for (const [index, ticket] of parsed.tickets.entries()) {
    if (!ticket || typeof ticket !== 'object')
      throw new Error(`Ticket ${index + 1} must be an object.`);
    for (const field of ['external_id', 'title', 'body', 'customer']) {
      if (typeof ticket[field] !== 'string' || !ticket[field].trim())
        throw new Error(`Ticket ${index + 1} needs a non-empty ${field}.`);
    }
    if (ticket.body.length > 10_000)
      throw new Error(`Ticket ${index + 1} body exceeds 10,000 characters.`);
    if (!['low', 'medium', 'high', 'urgent'].includes(ticket.priority))
      throw new Error(`Ticket ${index + 1} needs priority: low, medium, high, or urgent.`);
  }
  return { tickets: parsed.tickets as ImportedTicket[] };
}
