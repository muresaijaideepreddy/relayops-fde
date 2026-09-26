import { useCallback, useEffect, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleCheck,
  Clock3,
  Database,
  FileJson,
  FlaskConical,
  Inbox,
  Layers3,
  LoaderCircle,
  LockKeyhole,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Ticket as TicketIcon,
  TriangleAlert,
  Workflow,
  X,
} from 'lucide-react';
import { filterTickets, parseIngest, request } from './api';
import type {
  Action,
  Analysis,
  Audit,
  Document,
  Evaluation,
  Metrics,
  Ticket,
  Workspace,
} from './types';

type View = 'workspace' | 'approvals' | 'knowledge' | 'evaluations' | 'audit';
type Data = {
  workspace: Workspace;
  tickets: Ticket[];
  metrics: Metrics;
  actions: Action[];
  documents: Document[];
  audit: Audit[];
  evaluation: Evaluation | null;
};
const nav = [
  { id: 'workspace', name: 'Workbench', icon: Inbox },
  { id: 'approvals', name: 'Approvals', icon: ShieldCheck },
  { id: 'knowledge', name: 'Knowledge', icon: BookOpen },
  { id: 'evaluations', name: 'Evaluations', icon: FlaskConical },
  { id: 'audit', name: 'Activity log', icon: Activity },
] as const;
const pct = (value: number) => `${Math.round(value * 100)}%`;
const date = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
const label = (value: string) => value.replaceAll('_', ' ').replaceAll('.', ' · ');
const errorText = (error: unknown) =>
  error instanceof Error ? error.message : 'Something went wrong. Please try again.';
const sample = JSON.stringify(
  {
    tickets: [
      {
        external_id: 'IMPORT-1001',
        title: 'Shipment status update requested',
        body: 'Our delivery is delayed. Please confirm the next steps and escalation policy.',
        customer: 'Harbor Supply (synthetic)',
        priority: 'high',
      },
    ],
  },
  null,
  2,
);

function storedKey() {
  try {
    return sessionStorage.getItem('relayops-workspace-key') || 'northstar-demo-key';
  } catch {
    return 'northstar-demo-key';
  }
}

export default function App() {
  const [apiKey, setApiKey] = useState(storedKey);
  const [switchOpen, setSwitchOpen] = useState(false);
  const changeKey = (key: string) => {
    try {
      sessionStorage.setItem('relayops-workspace-key', key);
    } catch {
      /* Memory-only session when storage is unavailable. */
    }
    setApiKey(key);
    setSwitchOpen(false);
  };
  return (
    <>
      <WorkspaceSession key={apiKey} apiKey={apiKey} onSwitch={() => setSwitchOpen(true)} />
      {switchOpen && (
        <Modal title="Switch workspace" onClose={() => setSwitchOpen(false)}>
          <p className="muted">
            Each workspace has its own tickets, knowledge, approvals, and audit trail.
          </p>
          <div className="workspace-options">
            <button className="workspace-option" onClick={() => changeKey('northstar-demo-key')}>
              <span className="avatar">N</span>
              <span>
                <strong>Northstar Logistics</strong>
                <small>Synthetic logistics workspace</small>
              </span>
              <ArrowRight size={18} />
            </button>
            <button className="workspace-option" onClick={() => changeKey('meridian-demo-key')}>
              <span className="avatar lavender">M</span>
              <span>
                <strong>Meridian Retail</strong>
                <small>Synthetic retail workspace</small>
              </span>
              <ArrowRight size={18} />
            </button>
          </div>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const key = String(new FormData(event.currentTarget).get('key')).trim();
              if (key) changeKey(key);
            }}
          >
            <label className="field-label" htmlFor="workspace-key">
              Or enter a provisioned workspace key
            </label>
            <input
              autoComplete="off"
              type="password"
              id="workspace-key"
              name="key"
              placeholder="Workspace API key"
              required
            />
            <p className="field-hint">
              Stored only for this browser tab. Do not enter an AI provider key.
            </p>
            <button className="button primary" type="submit">
              Connect workspace <ArrowRight size={16} />
            </button>
          </form>
        </Modal>
      )}
    </>
  );
}

function WorkspaceSession({ apiKey, onSwitch }: { apiKey: string; onSwitch: () => void }) {
  const [data, setData] = useState<Data | null>(null);
  const [view, setView] = useState<View>('workspace');
  const [selectedId, setSelectedId] = useState('');
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const [modal, setModal] = useState<'ingest' | 'document' | null>(null);
  const [tab, setTab] = useState('overview');
  const session = useRef(new AbortController());
  const currentTicket = useRef(selectedId);
  currentTicket.current = selectedId;

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const options = { signal: session.current.signal };
      const [workspace, tickets, metrics, actions, documents, audit, evaluation] =
        await Promise.all([
          request<Workspace>('/workspace', apiKey, options),
          request<Ticket[]>('/tickets', apiKey, options),
          request<Metrics>('/metrics', apiKey, options),
          request<Action[]>('/actions', apiKey, options),
          request<Document[]>('/documents', apiKey, options),
          request<Audit[]>('/audit', apiKey, options),
          request<Evaluation | null>('/evaluations/latest', apiKey, options),
        ]);
      setData({ workspace, tickets, metrics, actions, documents, audit, evaluation });
      setSelectedId((previous) =>
        tickets.some((ticket) => ticket.id === previous) ? previous : tickets[0]?.id || '',
      );
      setError('');
    } catch (error) {
      if (!(error instanceof Error && error.name === 'AbortError')) {
        setError(errorText(error));
        throw error;
      }
    } finally {
      setRefreshing(false);
    }
  }, [apiKey]);

  useEffect(() => {
    session.current = new AbortController();
    void refresh().catch(() => undefined);
    return () => session.current.abort();
  }, [refresh]);

  useEffect(() => {
    const controller = new AbortController();
    setAnalysis(null);
    setAnalysisError('');
    setTab('overview');
    if (!selectedId) return;
    setAnalysisLoading(true);
    request<Analysis | null>(`/tickets/${encodeURIComponent(selectedId)}/analysis`, apiKey, {
      signal: controller.signal,
    })
      .then(setAnalysis)
      .catch((error) => {
        if (error.name !== 'AbortError') setAnalysisError(errorText(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) setAnalysisLoading(false);
      });
    return () => controller.abort();
  }, [apiKey, selectedId]);

  async function perform(name: string, task: () => Promise<unknown>, success: string) {
    if (busy) return;
    setBusy(name);
    setError('');
    setNotice('');
    try {
      await task();
      if (success) setNotice(success);
      await refresh();
    } catch (error) {
      if (!(error instanceof Error && error.name === 'AbortError')) setError(errorText(error));
    } finally {
      setBusy('');
    }
  }
  const post = <T,>(path: string, body?: unknown) =>
    request<T>(path, apiKey, {
      method: 'POST',
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
      signal: session.current.signal,
    });
  const analyze = () =>
    perform(
      'analyze',
      async () => {
        const id = selectedId;
        const result = await post<Analysis>(`/tickets/${encodeURIComponent(id)}/analyze`);
        if (currentTicket.current === id) {
          setAnalysis(result);
          setAnalysisError('');
          setTab('overview');
        }
      },
      'Analysis complete. Review the evidence before deciding on the proposed action.',
    );
  const decide = (action: Action, decision: 'approve' | 'reject', note: string) =>
    perform(
      action.id,
      () => post(`/actions/${encodeURIComponent(action.id)}/approve`, { decision, note }),
      decision === 'approve'
        ? 'Approved. A note was written to the local simulated CRM.'
        : 'Action rejected. No CRM note was written.',
    );
  const selected = data?.tickets.find((ticket) => ticket.id === selectedId);
  const pending = data?.actions.filter((action) => action.status === 'pending').length || 0;
  const visibleTickets = filterTickets(data?.tickets || [], query, filter);
  const selectedAction = data?.actions.find((action) => action.id === analysis?.action_id);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(event) => {
            event.preventDefault();
            setView('workspace');
          }}
          aria-label="RelayOps home"
        >
          <span className="brand-mark">
            <Workflow size={23} />
          </span>
          relay<span>ops</span>
          <span className="brand-dot" />
        </a>
        <div className="side-label">OPERATIONS</div>
        <nav aria-label="Main navigation">
          {nav.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${view === item.id ? 'active' : ''}`}
              aria-current={view === item.id ? 'page' : undefined}
              onClick={() => setView(item.id)}
            >
              <item.icon size={18} />
              <span>{item.name}</span>
              {item.id === 'approvals' && pending > 0 && (
                <span className="nav-count">{pending}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="safety-card">
            <ShieldCheck size={21} />
            <strong>Built for human judgment</strong>
            <p>Evidence first. Every action reviewed. Every decision traced.</p>
            <span>
              <span className="status-dot" />
              Tenant-scoped by design
            </span>
          </div>
          <button className="profile" onClick={onSwitch}>
            <span className="profile-avatar">RO</span>
            <span>
              <strong>Demo operator</strong>
              <small>Switch workspace</small>
            </span>
            <ChevronDown size={16} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <Layers3 size={16} />
            <span>Operations</span>
            <ChevronRight size={13} />
            <strong>{nav.find((item) => item.id === view)?.name}</strong>
          </div>
          <div className="topbar-right">
            <span className="mode-pill">
              <span className="status-dot" />
              {data?.workspace.mode === 'demo'
                ? 'Offline demo'
                : data
                  ? `${data.workspace.mode} mode`
                  : 'Connecting'}
            </span>
            <button className="workspace-switch" onClick={onSwitch}>
              <span className="tiny-avatar">{data?.workspace.tenant.name.slice(0, 1) || 'W'}</span>
              <span>{data?.workspace.tenant.name || 'Choose workspace'}</span>
              <ChevronDown size={14} />
            </button>
          </div>
        </header>
        <main id="main-content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                SUPPORT OPERATIONS /{' '}
                {view === 'workspace' ? 'WORKSPACE' : label(view).toUpperCase()}
              </div>
              <h1>
                {
                  {
                    workspace: 'Your queue, in focus.',
                    approvals: 'Keep people in the loop.',
                    knowledge: 'Give every answer a source.',
                    evaluations: 'Confidence, measured.',
                    audit: 'Every decision leaves a trail.',
                  }[view]
                }
              </h1>
              <p>
                {
                  {
                    workspace: 'Turn customer context into grounded answers and reviewed actions.',
                    approvals:
                      'Review the proposed action before anything reaches the simulated CRM.',
                    knowledge: 'A tenant-scoped source of truth for grounded ticket analysis.',
                    evaluations:
                      'Run a repeatable offline baseline against isolated test scenarios.',
                    audit: 'Follow the evidence, execution steps, and operator decisions.',
                  }[view]
                }
              </p>
            </div>
            <div className="heading-actions">
              <button
                className="button secondary icon-button"
                aria-label="Refresh workspace"
                disabled={refreshing || !!busy}
                onClick={() => {
                  void refresh().catch(() => undefined);
                }}
              >
                <RefreshCw size={17} className={refreshing ? 'spin' : ''} />
              </button>
              {view === 'workspace' && (
                <button
                  className="button primary"
                  onClick={() => setModal('ingest')}
                  disabled={!data || !!busy}
                >
                  <ArrowDownToLine size={16} />
                  Import tickets
                </button>
              )}
              {view === 'knowledge' && (
                <button
                  className="button primary"
                  onClick={() => setModal('document')}
                  disabled={!data || !!busy}
                >
                  <Plus size={17} />
                  Add document
                </button>
              )}
              {view === 'evaluations' && (
                <button
                  className="button primary"
                  disabled={!data || !!busy}
                  onClick={() => {
                    void perform(
                      'evaluation',
                      () => post('/evaluations/run'),
                      'Offline baseline completed. Results are saved to this workspace.',
                    );
                  }}
                >
                  <FlaskConical size={17} />
                  {busy === 'evaluation' ? 'Running baseline…' : 'Run baseline'}
                </button>
              )}
            </div>
          </div>
          {error && (
            <div className="alert error" role="alert">
              <TriangleAlert size={19} />
              <span>{error}</span>
              <button aria-label="Dismiss error" onClick={() => setError('')}>
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="alert success" role="status">
              <CircleCheck size={19} />
              <span>{notice}</span>
              <button aria-label="Dismiss notification" onClick={() => setNotice('')}>
                <X size={16} />
              </button>
            </div>
          )}
          {!data ? (
            <div className="panel connection-state">
              {refreshing ? <LoaderCircle size={30} className="spin" /> : <Database size={34} />}
              <h2>{refreshing ? 'Opening your workspace' : 'Your workspace is waiting'}</h2>
              <p>
                {refreshing
                  ? 'Loading tickets, knowledge, and activity securely.'
                  : 'Start the API server and refresh to load the synthetic demo workspace.'}
              </p>
              {!refreshing && (
                <button
                  className="button primary"
                  onClick={() => {
                    void refresh().catch(() => undefined);
                  }}
                >
                  Try connection again <RefreshCw size={16} />
                </button>
              )}
            </div>
          ) : (
            <>
              {view === 'workspace' && (
                <>
                  <div className="metric-grid">
                    <Metric
                      icon={<TicketIcon size={19} />}
                      name="Total tickets"
                      value={data.metrics.total_tickets}
                      note={`${data.metrics.open_tickets} awaiting analysis`}
                    />
                    <Metric
                      icon={<Sparkles size={19} />}
                      name="Analyzed"
                      value={data.metrics.analyzed_tickets}
                      note="Grounded in workspace knowledge"
                    />
                    <Metric
                      icon={<ShieldCheck size={19} />}
                      name="Needs approval"
                      value={data.metrics.pending_approvals}
                      note="You have the final say"
                      accent="amber"
                    />
                    <Metric
                      icon={<CheckCheck size={19} />}
                      name="Approved actions"
                      value={data.metrics.approved_actions}
                      note="Local simulated CRM notes"
                      accent="teal"
                    />
                  </div>
                  <div className="workflow-banner">
                    <span className="workflow-symbol">
                      <Workflow size={20} />
                    </span>
                    <div>
                      <strong>Context in. Confidence out.</strong>
                      <span>Retrieve evidence, review the answer, approve the next step.</span>
                    </div>
                    <div className="pipeline">
                      <span>Ingest</span>
                      <ChevronRight size={13} />
                      <span>Ground</span>
                      <ChevronRight size={13} />
                      <span>Review</span>
                      <ChevronRight size={13} />
                      <span>Act</span>
                    </div>
                  </div>
                  <div className="workbench-grid">
                    <section className="panel queue-panel">
                      <div className="panel-heading">
                        <h2>
                          Ticket queue <span className="count">{data.tickets.length}</span>
                        </h2>
                        <span className="subtle-label">TENANT SCOPED</span>
                      </div>
                      <div className="queue-tools">
                        <div className="search-field">
                          <Search size={17} />
                          <input
                            aria-label="Search tickets"
                            placeholder="Search tickets or customers…"
                            value={query}
                            onChange={(event) => setQuery(event.target.value)}
                          />
                        </div>
                        <select
                          aria-label="Filter tickets by status"
                          value={filter}
                          onChange={(event) => setFilter(event.target.value)}
                        >
                          <option value="all">All statuses</option>
                          <option value="open">Open</option>
                          <option value="in_review">In review</option>
                          <option value="reviewed">Reviewed</option>
                        </select>
                      </div>
                      <div className="queue-column-labels">
                        <span>TICKET / CUSTOMER</span>
                        <span>PRIORITY</span>
                      </div>
                      <div className="ticket-list">
                        {visibleTickets.map((ticket) => (
                          <button
                            key={ticket.id}
                            className={`ticket-row ${ticket.id === selectedId ? 'selected' : ''}`}
                            onClick={() => setSelectedId(ticket.id)}
                            aria-pressed={ticket.id === selectedId}
                          >
                            <div className="ticket-content">
                              <div className="ticket-meta">
                                <span>{ticket.external_id}</span>
                                <span className={`ticket-status ${ticket.status}`}>
                                  <i />
                                  {label(ticket.status)}
                                </span>
                              </div>
                              <strong>{ticket.title}</strong>
                              <div className="ticket-customer">
                                <span className="customer-avatar">
                                  {ticket.customer.slice(0, 1)}
                                </span>
                                {ticket.customer}
                              </div>
                            </div>
                            <div className="ticket-right">
                              <span className={`badge ${ticket.priority}`}>{ticket.priority}</span>
                              <ChevronRight size={16} />
                            </div>
                          </button>
                        ))}
                        {!visibleTickets.length && (
                          <Empty
                            icon={<Inbox size={28} />}
                            title="No tickets found"
                            text={
                              data.tickets.length
                                ? 'Try another search or status filter.'
                                : 'Import a JSON batch to start your queue.'
                            }
                          />
                        )}
                      </div>
                      <div className="queue-footer">
                        <span>
                          {visibleTickets.length} of {data.tickets.length} tickets
                        </span>
                        <span>
                          <LockKeyhole size={12} />
                          Workspace isolated
                        </span>
                      </div>
                    </section>
                    <section className="panel detail-panel" aria-label="Ticket details">
                      {selected ? (
                        <>
                          <div className="detail-top">
                            <div>
                              <span className="eyebrow">TICKET INTELLIGENCE</span>
                              <div className="detail-id">
                                {selected.external_id}
                                <span className={`badge ${selected.priority}`}>
                                  {selected.priority}
                                </span>
                              </div>
                            </div>
                            <span className="intelligence-icon">
                              <Sparkles size={21} />
                            </span>
                          </div>
                          <h2 className="detail-title">{selected.title}</h2>
                          <div className="detail-person">
                            <span className="customer-avatar">{selected.customer.slice(0, 1)}</span>
                            {selected.customer}
                            <span className="detail-separator">·</span>
                            {date(selected.created_at)}
                          </div>
                          <div
                            className="detail-tabs"
                            role="tablist"
                            aria-label="Ticket analysis views"
                          >
                            {[
                              { id: 'overview', name: 'Overview' },
                              { id: 'evidence', name: 'Evidence' },
                              { id: 'trace', name: 'Run trace' },
                            ].map((item) => (
                              <button
                                role="tab"
                                aria-selected={tab === item.id}
                                id={`tab-${item.id}`}
                                aria-controls={`panel-${item.id}`}
                                tabIndex={tab === item.id ? 0 : -1}
                                onKeyDown={(event) => {
                                  if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
                                    const tabs = ['overview', 'evidence', 'trace'];
                                    const next =
                                      tabs[
                                        (tabs.indexOf(tab) + (event.key === 'ArrowRight' ? 1 : 2)) %
                                          3
                                      ];
                                    setTab(next);
                                    document.getElementById(`tab-${next}`)?.focus();
                                  }
                                }}
                                className={tab === item.id ? 'active' : ''}
                                key={item.id}
                                onClick={() => setTab(item.id)}
                              >
                                {item.name}
                                {item.id === 'evidence' && !!analysis?.citations.length && (
                                  <span>{analysis.citations.length}</span>
                                )}
                              </button>
                            ))}
                          </div>
                          <div
                            className="detail-body"
                            role="tabpanel"
                            id={`panel-${tab}`}
                            aria-labelledby={`tab-${tab}`}
                          >
                            {analysisError && (
                              <div className="inline-error" role="alert">
                                {analysisError}
                              </div>
                            )}
                            {analysisLoading ? (
                              <div className="loading-inline">
                                <LoaderCircle size={19} className="spin" />
                                Loading analysis…
                              </div>
                            ) : tab === 'overview' ? (
                              <>
                                <div className="section-kicker">
                                  <span className="section-dot" />
                                  CUSTOMER CONTEXT
                                </div>
                                <p className="ticket-body">{selected.body}</p>
                                {analysis ? (
                                  <>
                                    <div className="analysis-header">
                                      <h3>
                                        <Sparkles size={16} />
                                        Analysis
                                      </h3>
                                      <span className="tag teal">
                                        {analysis.provider === 'demo'
                                          ? 'Deterministic demo'
                                          : label(analysis.provider)}
                                      </span>
                                    </div>
                                    <p className="analysis-summary">{analysis.summary}</p>
                                    <div className="signal-row">
                                      <span title="Heuristic score; not a calibrated probability of correctness.">
                                        <ShieldCheck size={14} />
                                        {pct(analysis.confidence)} heuristic confidence
                                      </span>
                                      <span className={`risk-${analysis.risk}`}>
                                        {analysis.risk} risk
                                      </span>
                                      <span>
                                        <Clock3 size={13} />
                                        {Math.round(analysis.latency_ms)} ms
                                      </span>
                                    </div>
                                    {analysis.needs_escalation && (
                                      <div className="escalation">
                                        <TriangleAlert size={16} />
                                        Human escalation recommended
                                      </div>
                                    )}
                                    <div className="recommendation">
                                      <div className="section-kicker">RECOMMENDED NEXT STEP</div>
                                      <p>{analysis.recommended_action}</p>
                                    </div>
                                    <div className="draft-card">
                                      <div className="draft-heading">
                                        <h3>Suggested reply</h3>
                                        <span className="tag">Draft only</span>
                                      </div>
                                      <p>{analysis.draft_reply}</p>
                                    </div>
                                    {selectedAction && (
                                      <div className="approval-inline">
                                        <div>
                                          <ShieldCheck size={16} />
                                          <strong>
                                            {selectedAction.status === 'pending'
                                              ? 'Ready for your review'
                                              : `Action ${selectedAction.status}`}
                                          </strong>
                                        </div>
                                        <p>
                                          {selectedAction.status === 'pending'
                                            ? 'Approval saves a local simulated CRM note. It does not send this reply to the customer.'
                                            : 'See Approvals for the saved decision and connector result.'}
                                        </p>
                                        <button
                                          className="button secondary full"
                                          onClick={() => setView('approvals')}
                                        >
                                          Review proposed action <ArrowRight size={15} />
                                        </button>
                                      </div>
                                    )}
                                  </>
                                ) : (
                                  <div className="analysis-empty">
                                    <span className="analysis-empty-icon">
                                      <Sparkles size={24} />
                                    </span>
                                    <h3>Good answers start with evidence.</h3>
                                    <p>
                                      Analyze this ticket to retrieve relevant knowledge, assess
                                      risk, and prepare a reviewable next step.
                                    </p>
                                    <div className="analysis-guarantees">
                                      <span>
                                        <Check size={13} />
                                        Tenant-scoped sources
                                      </span>
                                      <span>
                                        <Check size={13} />
                                        Human approval
                                      </span>
                                    </div>
                                  </div>
                                )}
                              </>
                            ) : tab === 'evidence' ? (
                              <>
                                {analysis?.citations.length ? (
                                  <>
                                    <div className="evidence-intro">
                                      <ShieldCheck size={19} />
                                      <span>
                                        Retrieved from this workspace's knowledge. Verify each
                                        source before approval.
                                      </span>
                                    </div>
                                    {analysis.citations.map((citation, index) => (
                                      <article
                                        className="citation-card"
                                        key={`${citation.document_id}-${index}`}
                                      >
                                        <div className="citation-heading">
                                          <span className="citation-number">{index + 1}</span>
                                          <h3>{citation.title}</h3>
                                        </div>
                                        <p>{citation.excerpt}</p>
                                        <footer>
                                          <span>Retrieval score</span>
                                          <strong>{citation.score.toFixed(3)}</strong>
                                        </footer>
                                      </article>
                                    ))}
                                  </>
                                ) : (
                                  <Empty
                                    icon={<BookOpen size={27} />}
                                    title={
                                      analysis
                                        ? 'No supporting sources'
                                        : 'Evidence will appear here'
                                    }
                                    text={
                                      analysis
                                        ? 'Treat this analysis as ungrounded. Add relevant knowledge and reanalyze.'
                                        : 'Analyze the ticket to retrieve workspace knowledge.'
                                    }
                                  />
                                )}
                              </>
                            ) : (
                              <>
                                {analysis ? (
                                  <>
                                    <div className="trace-caption">
                                      <span className="tag">{label(analysis.provider)}</span>
                                      <span>{Math.round(analysis.latency_ms)} ms total</span>
                                    </div>
                                    <ol className="trace-list">
                                      {analysis.steps.map((step, index) => (
                                        <li key={`${step.name}-${index}`}>
                                          <span
                                            className={`trace-marker ${step.status === 'completed' ? 'completed' : step.status === 'pending' ? 'pending' : 'attention'}`}
                                            aria-label={label(step.status)}
                                          >
                                            {step.status === 'completed' ? (
                                              <Check size={13} />
                                            ) : step.status === 'pending' ? (
                                              <Clock3 size={13} />
                                            ) : (
                                              <TriangleAlert size={13} />
                                            )}
                                          </span>
                                          <div>
                                            <div className="trace-step-head">
                                              <strong>{label(step.name)}</strong>
                                              <span>{Math.round(step.duration_ms)} ms</span>
                                            </div>
                                            <p>{step.detail}</p>
                                            <small>{label(step.status)}</small>
                                          </div>
                                        </li>
                                      ))}
                                    </ol>
                                  </>
                                ) : (
                                  <Empty
                                    icon={<Workflow size={28} />}
                                    title="An inspectable path to an answer"
                                    text="Every analysis records retrieval, reasoning, and action preparation steps."
                                  />
                                )}
                              </>
                            )}
                          </div>
                          <div className="detail-footer">
                            <span>
                              <LockKeyhole size={13} />
                              {data.workspace.mode === 'demo'
                                ? 'No external AI calls in demo mode'
                                : 'Configured AI provider enabled'}
                            </span>
                            <button
                              className="button primary"
                              disabled={!!busy || analysisLoading}
                              onClick={() => {
                                void analyze();
                              }}
                            >
                              {busy === 'analyze' ? (
                                <LoaderCircle size={15} className="spin" />
                              ) : (
                                <Sparkles size={15} />
                              )}
                              {busy === 'analyze'
                                ? 'Analyzing…'
                                : analysis
                                  ? 'Reanalyze ticket'
                                  : 'Analyze ticket'}
                              {busy !== 'analyze' && <ArrowRight size={15} />}
                            </button>
                          </div>
                        </>
                      ) : (
                        <Empty
                          icon={<TicketIcon size={30} />}
                          title="Select a ticket to get started"
                          text="Customer context, source evidence, and proposed actions will appear here."
                        />
                      )}
                    </section>
                  </div>
                </>
              )}
              {view === 'approvals' && (
                <>
                  <div className="info-strip">
                    <ShieldCheck size={21} />
                    <span>
                      <strong>Local simulated connector.</strong> Approval writes a CRM note inside
                      this application. No customer messages, refunds, or external CRM changes are
                      sent.
                    </span>
                  </div>
                  <div className="section-title">
                    <h2>
                      Proposed actions <span className="count">{data.actions.length}</span>
                    </h2>
                    <span>{pending} awaiting review</span>
                  </div>
                  {data.actions.length ? (
                    <div className="action-grid">
                      {data.actions.map((action) => (
                        <ApprovalCard
                          key={action.id}
                          action={action}
                          ticket={data.tickets.find((ticket) => ticket.id === action.ticket_id)}
                          disabled={!!busy}
                          working={busy === action.id}
                          onDecide={decide}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="panel">
                      <Empty
                        icon={<ShieldCheck size={32} />}
                        title="Your approval queue is clear"
                        text="Analyze a ticket in the workbench to prepare an action for review."
                      />
                      <div className="empty-action">
                        <button className="button primary" onClick={() => setView('workspace')}>
                          Open workbench <ArrowRight size={15} />
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
              {view === 'knowledge' && (
                <>
                  <div className="info-strip">
                    <Database size={20} />
                    <span>
                      <strong>{data.documents.length} source documents.</strong> New documents are
                      available for the next analysis. Sources belong only to{' '}
                      {data.workspace.tenant.name}.
                    </span>
                  </div>
                  <div className="document-grid">
                    {data.documents.map((document) => (
                      <article className="panel document-card" key={document.id}>
                        <span className="document-icon">
                          <BookOpen size={22} />
                        </span>
                        <span className="tag teal">Workspace source</span>
                        <h2>{document.title}</h2>
                        <p className="document-source">{document.source}</p>
                        <p className="document-preview">{document.content}</p>
                        <details>
                          <summary>
                            Read full document <ArrowUpRight size={14} />
                          </summary>
                          <p className="full-document">{document.content}</p>
                        </details>
                        <footer>
                          <span>{document.content.length.toLocaleString()} characters</span>
                          <span>{date(document.created_at)}</span>
                        </footer>
                      </article>
                    ))}
                  </div>
                  {!data.documents.length && (
                    <div className="panel">
                      <Empty
                        icon={<BookOpen size={30} />}
                        title="Build your knowledge base"
                        text="Add a policy, runbook, or procedure so the copilot can cite its sources."
                      />
                    </div>
                  )}
                </>
              )}
              {view === 'evaluations' && <EvaluationView evaluation={data.evaluation} />}
              {view === 'audit' && (
                <section className="panel">
                  <div className="panel-heading">
                    <h2>
                      Workspace activity <span className="count">{data.audit.length}</span>
                    </h2>
                    <span className="subtle-label">PERSISTED AUDIT EVENTS</span>
                  </div>
                  {data.audit.length ? (
                    <div className="audit-list">
                      {data.audit.map((event) => (
                        <article className="audit-row" key={event.id}>
                          <span className="audit-icon">
                            <Activity size={17} />
                          </span>
                          <div>
                            <div className="audit-heading">
                              <h3>{label(event.event)}</h3>
                              <time dateTime={event.created_at}>{date(event.created_at)}</time>
                            </div>
                            <span className="mono entity-id">{event.entity_id}</span>
                            <details>
                              <summary>
                                Inspect event data <ChevronDown size={13} />
                              </summary>
                              <pre>{JSON.stringify(event.detail, null, 2)}</pre>
                            </details>
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <Empty
                      icon={<Activity size={30} />}
                      title="A clear starting point"
                      text="Import documents, analyze tickets, or approve actions to create audit events."
                    />
                  )}
                </section>
              )}
              <footer className="page-footer">
                <span>
                  <span className="status-dot" />
                  {data.workspace.mode === 'demo'
                    ? 'Offline deterministic demo'
                    : `${data.workspace.mode} provider`}
                  <span className="footer-divider">/</span>
                  {['northstar', 'meridian'].includes(data.workspace.tenant.id)
                    ? 'Synthetic customer data'
                    : 'Tenant-scoped workspace'}
                </span>
                <span>
                  Built for the work between insight and action <ArrowUpRight size={12} />
                </span>
              </footer>
            </>
          )}
        </main>
      </div>
      {modal === 'ingest' && (
        <Modal title="Import a ticket batch" onClose={() => setModal(null)} busy={!!busy}>
          <p className="muted">
            Paste JSON from a source system. Up to 100 tickets per batch; duplicate external IDs are
            skipped within this workspace.
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              try {
                const payload = parseIngest(String(new FormData(event.currentTarget).get('json')));
                void perform(
                  'ingest',
                  async () => {
                    const result = await post<{ imported: number; skipped: number }>(
                      '/ingest',
                      payload,
                    );
                    setModal(null);
                    setNotice(
                      `Imported ${result.imported} tickets; skipped ${result.skipped} duplicates.`,
                    );
                  },
                  '',
                );
              } catch (error) {
                setError(errorText(error));
              }
            }}
          >
            <label className="field-label" htmlFor="import-json">
              Ticket JSON
            </label>
            <textarea
              className="code-input"
              id="import-json"
              name="json"
              defaultValue={sample}
              rows={13}
              required
            />
            {error && (
              <p className="inline-error" role="alert">
                {error}
              </p>
            )}
            <div className="modal-footer">
              <span>
                <FileJson size={16} />
                JSON · Idempotent import
              </span>
              <button type="submit" className="button primary" disabled={!!busy}>
                {busy === 'ingest' ? 'Importing…' : 'Import tickets'}
                <ArrowRight size={15} />
              </button>
            </div>
          </form>
        </Modal>
      )}
      {modal === 'document' && (
        <Modal title="Add knowledge document" onClose={() => setModal(null)} busy={!!busy}>
          <p className="muted">Add a source that operators can verify and the copilot can cite.</p>
          <form
            onSubmit={(event: FormEvent<HTMLFormElement>) => {
              event.preventDefault();
              const fields = new FormData(event.currentTarget);
              const payload = {
                title: String(fields.get('title')).trim(),
                source: String(fields.get('source')).trim(),
                content: String(fields.get('content')).trim(),
              };
              if (!payload.title || !payload.source || !payload.content) {
                setError('All document fields must contain text.');
                return;
              }
              void perform(
                'document',
                async () => {
                  await post('/documents', payload);
                  setModal(null);
                },
                'Knowledge document added. Reanalyze a ticket to include the new source.',
              );
            }}
          >
            <label className="field-label" htmlFor="doc-title">
              Title
            </label>
            <input
              id="doc-title"
              name="title"
              placeholder="e.g. Delivery escalation policy"
              maxLength={240}
              required
            />
            <label className="field-label" htmlFor="doc-source">
              Source reference
            </label>
            <input
              id="doc-source"
              name="source"
              placeholder="e.g. internal://support/delivery-policy"
              maxLength={500}
              required
            />
            <label className="field-label" htmlFor="doc-content">
              Document content
            </label>
            <textarea
              id="doc-content"
              name="content"
              rows={9}
              maxLength={20000}
              placeholder="Paste the policy or procedure, including important conditions and exceptions…"
              required
            />
            <p className="field-hint">
              Maximum 20,000 characters. Text is stored only in the current workspace.
            </p>
            {error && (
              <p className="inline-error" role="alert">
                {error}
              </p>
            )}
            <div className="modal-footer">
              <span>
                <LockKeyhole size={15} />
                Tenant-scoped knowledge
              </span>
              <button type="submit" className="button primary" disabled={!!busy}>
                {busy === 'document' ? 'Saving…' : 'Add document'}
                <Plus size={15} />
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}

function Metric({
  icon,
  name,
  value,
  note,
  accent = 'blue',
}: {
  icon: ReactNode;
  name: string;
  value: number | string;
  note: string;
  accent?: string;
}) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span>{name}</span>
        <span className={`metric-icon ${accent}`}>{icon}</span>
      </div>
      <strong className="metric-value">{value}</strong>
      <span className="metric-note">{note}</span>
    </article>
  );
}

function Empty({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="empty-state">
      <span>{icon}</span>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function Modal({
  title,
  children,
  onClose,
  busy = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      aria-label={title}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current && !busy) {
          const bounds = ref.current.getBoundingClientRect();
          if (
            event.clientX < bounds.left ||
            event.clientX > bounds.right ||
            event.clientY < bounds.top ||
            event.clientY > bounds.bottom
          )
            onClose();
        }
      }}
    >
      <div className="modal-header">
        <h2>{title}</h2>
        <button
          className="icon-button button secondary"
          aria-label="Close dialog"
          onClick={onClose}
          disabled={busy}
        >
          <X size={19} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

function ApprovalCard({
  action,
  ticket,
  disabled,
  working,
  onDecide,
}: {
  action: Action;
  ticket?: Ticket;
  disabled: boolean;
  working: boolean;
  onDecide: (action: Action, decision: 'approve' | 'reject', note: string) => Promise<void>;
}) {
  const [note, setNote] = useState('');
  return (
    <article className="panel approval-card">
      <div className="approval-card-header">
        <span className="section-kicker">
          <ShieldCheck size={15} />
          SIMULATED CRM NOTE
        </span>
        <span
          className={`tag ${action.status === 'pending' ? 'amber' : action.status === 'approved' ? 'teal' : ''}`}
        >
          {label(action.status)}
        </span>
      </div>
      <span className="eyebrow">{ticket?.external_id || action.ticket_id}</span>
      <h2>{ticket?.title || 'Ticket action'}</h2>
      <div className="action-payload">
        <h3>Proposed payload</h3>
        <pre>{JSON.stringify(action.payload, null, 2)}</pre>
      </div>
      {action.status === 'pending' ? (
        <>
          <label className="field-label" htmlFor={`note-${action.id}`}>
            Review note <span className="optional">(optional)</span>
          </label>
          <textarea
            id={`note-${action.id}`}
            rows={2}
            maxLength={2000}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Record the reason for your decision…"
          />
          <div className="approval-buttons">
            <button
              className="button secondary"
              disabled={disabled}
              onClick={() => {
                void onDecide(action, 'reject', note);
              }}
            >
              <X size={15} />
              Reject
            </button>
            <button
              className="button primary"
              disabled={disabled}
              onClick={() => {
                void onDecide(action, 'approve', note);
              }}
            >
              {working ? <LoaderCircle size={15} className="spin" /> : <Check size={15} />}Approve
              local note
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="decision-time">
            <CircleCheck size={15} />
            {label(action.status)} {action.decided_at ? date(action.decided_at) : ''}
          </p>
          {action.result && (
            <details>
              <summary>
                View saved connector result <ChevronDown size={14} />
              </summary>
              <pre>{JSON.stringify(action.result, null, 2)}</pre>
            </details>
          )}
        </>
      )}
    </article>
  );
}

function EvaluationView({ evaluation }: { evaluation: Evaluation | null }) {
  return (
    <>
      <div className="info-strip">
        <FlaskConical size={20} />
        <span>
          <strong>Offline baseline evaluation.</strong> Fixed fixtures run independently of
          workspace tickets and knowledge. These results validate the deterministic demo, not a live
          model's quality.
        </span>
      </div>
      {evaluation ? (
        <>
          <div className="evaluation-metrics">
            <Metric
              icon={<FlaskConical size={19} />}
              name="Baseline pass rate"
              value={pct(evaluation.pass_rate)}
              note={`${evaluation.passed} of ${evaluation.total} cases passed`}
              accent="teal"
            />
            <Metric
              icon={<CheckCheck size={19} />}
              name="Scenarios tested"
              value={evaluation.total}
              note="Isolated, repeatable test fixtures"
            />
            <article className="evaluation-run panel">
              <span className="section-kicker">LATEST SAVED RUN</span>
              <strong>{date(evaluation.created_at)}</strong>
              <span className="mono">{evaluation.id}</span>
              <span className="tag teal">Deterministic baseline</span>
            </article>
          </div>
          <section className="panel">
            <div className="panel-heading">
              <h2>Scenario results</h2>
              <span className="subtle-label">EXPECTED VS. ACTUAL</span>
            </div>
            <div className="evaluation-cases">
              {evaluation.cases.map((item) => (
                <article className="evaluation-case" key={item.id}>
                  <div className="case-heading">
                    <span className={`case-status ${item.passed ? 'passed' : 'failed'}`}>
                      {item.passed ? <Check size={17} /> : <X size={17} />}
                    </span>
                    <h3>{item.name}</h3>
                    <span className={`tag ${item.passed ? 'teal' : 'amber'}`}>
                      {item.passed ? 'Passed' : 'Failed'}
                    </span>
                    <span className="case-latency">{Math.round(item.latency_ms)} ms</span>
                  </div>
                  <div className="case-comparison">
                    <div>
                      <span>EXPECTED</span>
                      <p>{item.expected}</p>
                    </div>
                    <div>
                      <span>ACTUAL</span>
                      <p>{item.actual}</p>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </>
      ) : (
        <div className="panel evaluation-empty">
          <Empty
            icon={<FlaskConical size={35} />}
            title="Trust is a testable property."
            text="Run the baseline to inspect expected and actual behavior across the demo's fixed evaluation scenarios."
          />
          <div className="evaluation-promises">
            <span>
              <ShieldCheck size={17} />
              Isolated fixtures
            </span>
            <span>
              <RefreshCw size={17} />
              Repeatable results
            </span>
            <span>
              <Database size={17} />
              Saved run history
            </span>
          </div>
        </div>
      )}
    </>
  );
}
