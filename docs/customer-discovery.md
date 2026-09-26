# Customer discovery and pilot plan

RelayOps is a portfolio case study. **Northstar Logistics and Meridian Retail are fictional organizations; all included tickets, people, policies, and outcomes are synthetic.** This document is a proposed discovery exercise, not a record of interviews or a customer deployment.

## Problem hypothesis

A support operator has a queue of tickets, policy documents, and a separate CRM. Preparing an answer requires finding the relevant policy, interpreting the customer's request, and recording the decision. A useful first deployment would assemble evidence and prepare a reviewable next step while leaving judgment with the operator.

The hypothesis is that an evidence-first workbench can make this process easier to review. No reduction in handling time, cost, or error rate has been measured with real users.

## Stakeholders and questions

| Stakeholder | Questions to resolve before a real pilot | Decision informed |
| --- | --- | --- |
| Support operator | Walk through three recent tickets. Where do you look for policy? Which cases need supervisor judgment? What makes a draft unusable? | Workflow, interface, and escalation rules |
| Support lead | How are quality and handling time measured today? Which ticket category has enough volume and low enough consequence for a pilot? | Cohort selection and baseline |
| Knowledge owner | Who approves policies? How are versions, expiry, and conflicting documents handled? | Authoritative sources and retrieval scope |
| CRM owner | What stable IDs, rate limits, permissions, retries, and sandbox environments exist? | Connector design and failure recovery |
| Security and privacy owner | Which fields may leave the environment? Who can view or approve each tenant's tickets? What retention and deletion rules apply? | Identity, access, data handling, and provider choice |
| Executive sponsor | What outcome would justify continued investment? Who owns adoption after handoff? | Success criteria and operating ownership |

The missing answers remain assumptions. The repository makes those assumptions inspectable rather than presenting them as customer findings.

## First slice and acceptance criteria

The first slice is: import a ticket, retrieve evidence from that tenant's knowledge, produce structured analysis, review a proposed action, and record a simulated CRM note only after approval.

| Requirement | Acceptance demonstration |
| --- | --- |
| Tenant boundaries | A key for one tenant cannot read or mutate another tenant's ticket, analysis, action, document, audit record, or evaluation. |
| Repeatable intake | Importing a ticket with the same `external_id` twice within one tenant creates only one ticket. The same external ID may exist in another tenant. |
| Evidence before recommendation | Analysis exposes the documents and excerpts used. Insufficient evidence leads to an explicit cautious response or escalation. |
| Review before side effect | An analysis produces a pending action. It does not execute the connector. |
| Decision integrity | Repeating an approval returns the saved result; a conflicting second decision is rejected. Rejection does not write a CRM note. |
| Inspectable operation | The workbench shows analysis steps, measured latency, action status, and audit history. |
| Controlled integration | Approval writes only to a local simulated CRM. It does not send an email, issue a refund, or contact a real customer. |
| Repeatable evaluation | The evaluation endpoint uses isolated deterministic fixtures and reports case results. Workspace edits cannot silently change the benchmark. |
| Clear failure states | Missing or invalid credentials, unavailable API, invalid input, and provider failure return actionable errors rather than fabricated successful results. |

See [validation](validation.md) for the checks actually executed on this revision. A proposed criterion is not a claim that a test has passed.

## Proposed pilot measurement

Before enabling a real provider or connector, agree on the cohort, consent/data permissions, baseline sample, rubric, review owner, and stop conditions. Proposed stages are shadow mode, assisted drafting, and only then a narrowly permissioned write integration.

| Measure | Collection method | Interpretation |
| --- | --- | --- |
| Draft acceptance | Operator labels each draft accepted, edited, or rejected, with a reason | Usefulness; edits should be reviewed by category |
| Evidence quality | A policy owner grades citation relevance and whether each recommendation is supported | Quality beyond merely having a citation |
| Handling time | Compare the same eligible ticket category with a pre-pilot baseline; report medians, spread, and sample size | Workflow effect; the repository currently provides no result |
| Escalation quality | Review missed escalations and unnecessary escalations separately | Whether conservative handling is appropriate |
| Reliability | Record completion rate, provider errors, and latency percentiles | Operational readiness under the pilot load |
| Boundary failures | Review tenant-isolation and approval-bypass failures; any confirmed failure pauses the pilot | Safety of the workflow's access and action boundaries |

The sponsor and operators should set numeric thresholds after measuring a baseline. Do not convert the deterministic demo pass rate into a model accuracy score or a business-impact percentage.

## Delivery and handoff

1. Validate the workflow and choose one ticket category with the stakeholders above.
2. Run this offline prototype with synthetic data and review each acceptance criterion.
3. Implement the missing identity, operational, and connector controls described in [architecture](architecture.md).
4. Build a representative held-out evaluation set with the knowledge owner and review its failure cases.
5. Run the limited pilot, publish measured results and limitations, and assign an operational owner.

The handoff package consists of the code, [architecture](architecture.md), [runbook](runbook.md), [validation](validation.md), and the failure cases that remain open. Real adoption and production rollout are future work.
