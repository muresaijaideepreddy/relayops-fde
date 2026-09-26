# Interview guide

Describe RelayOps as an **independent portfolio project using synthetic data**. Northstar Logistics and Meridian Retail are fictional. Do not present the project as employment, a paid engagement, a production rollout, or evidence of a measured efficiency gain.

## A 60-second explanation

> I built RelayOps to demonstrate a forward deployed engineering workflow around support operations. The application imports tenant-scoped tickets, retrieves policy evidence, creates structured analysis, and requires a human decision before writing a simulated CRM note. I used React and TypeScript for the workbench and FastAPI with SQLAlchemy for the backend. The default provider is deterministic so reviewers can run the project without credentials; there is also an explicit OpenAI integration path. I included evaluations, audit history, discovery questions, and a runbook because delivery includes explaining what can fail and how to operate it. The customers and data are synthetic, and I have not measured real customer impact.

Adapt this script after personally running and understanding the code. Explain assistance received if asked; claim only work and decisions you can defend.

## Five-minute demonstration

1. **Frame the operator's task.** Explain the ticket-to-policy-to-CRM workflow and show the [discovery assumptions](customer-discovery.md).
2. **Analyze one ticket.** Open its evidence and step trace. Explain why a document is relevant, what confidence means, and why the proposed reply still needs review.
3. **Inspect the action.** Show the pending state, approve the simulated note, and show the persisted result and audit event. Explain what a repeated approval does.
4. **Switch tenants.** Show a different workspace and describe how the backend enforces its boundary. A different UI view by itself does not prove isolation; point to the API tests.
5. **Run the evaluation.** Show case-level failures or passes and the deterministic baseline label. Explain why this does not measure live-model accuracy.
6. **Close with the next experiment.** Describe how a real pilot would measure draft usefulness, citation quality, handling time, and operational reliability.

## Questions to prepare for

| Question | A defensible answer |
| --- | --- |
| Why is this an FDE project? | It connects a concrete workflow, discovery assumptions, a working vertical slice, integration boundaries, acceptance criteria, and an operating handoff. The docs distinguish the prototype from a real customer deployment. |
| Why not use vector search immediately? | The small synthetic policy corpus supports inspectable lexical retrieval. A labeled retrieval set should show where it fails before introducing embeddings, indexing lifecycle, and a vector service. |
| What prevents cross-tenant leakage? | The API resolves identity from a key and scopes data reads and mutations to that tenant. Explain the test coverage and remaining production concerns rather than claiming complete security. |
| Is human approval an authorization system? | No. It is a workflow decision point. This demo does not implement individual reviewer roles or separation of duties. |
| How do you prevent repeated actions? | The action keeps its final decision and saved result. An identical retry returns the result; a conflicting decision is rejected. A real remote CRM would also need durable delivery and reconciliation semantics. |
| How do you evaluate it? | Offline regression cases verify predictable application behavior. A live model needs a separate held-out, representative dataset, policy-owner grading, and error analysis. |
| What does the confidence number mean? | It is the provider's application-level score, not calibrated probability. I would avoid using it as an automatic permission to execute actions. |
| What happens when the model fails? | The API reports an error and avoids treating invalid provider output as an approved action. The exact observed behavior is documented in validation; live-provider behavior requires separate testing. |
| How would it scale? | First measure bottlenecks. Likely steps are PostgreSQL with migrations, background jobs for slow provider calls, bounded retries, quotas, and operational telemetry. Those are proposed extensions, not current production claims. |
| What did you learn from customers? | No customer interviews were conducted for this portfolio. The discovery document lists the questions I would ask and the assumptions I would validate. |

## Evidence to have ready

Keep the application running, the [architecture](architecture.md) open, and the [validation record](validation.md) available. Know where identity is resolved, where queries are tenant-scoped, how the provider output is validated, and where an approval becomes a connector call. Be ready to run one test and explain why it matters.

For impact questions, use an honest next-step answer: “This project demonstrates the implementation. To claim a time saving, I would first run the pilot plan with a representative cohort and report the baseline, sample size, measurement method, and results.”
