# Labelling rubric: grants → method (v1, 2026-08-20)

The risk rubric (`rubric.md`) asks *which harm* a grant is about. This one asks *what
kind of work* the grant pays for. Each grant gets **one method label**, a **confidence**,
and a **basis** of at most ten words.

The labels are the 23 subcategories of the MIT AI Risk Mitigation Database's control
taxonomy (draft, codes `1.1`–`4.6` below) **plus seven labels of our own**. The MIT
taxonomy describes controls that an AI developer, deployer or regulator implements; most
grants in this data pay for research, talent or advocacy *about* such controls rather
than for implementing them, and the MIT taxonomy has no place for interpretability
research, agent foundations, forecasting or public communication. The seven extra labels
are ours and are marked `X.*` so the two sets cannot be confused.

## Our labels (`X.*`)

| label | use when |
|---|---|
| `X.research-interp` | interpretability / mechanistic interpretability / transparency-of-internals research |
| `X.research-theory` | conceptual, mathematical or agent-foundations work on alignment, agency, decision theory, formal verification of AI |
| `X.research-empirical` | empirical ML safety research that is not interpretability and not an evaluation/audit product: alignment training methods, robustness, control protocols, scalable oversight experiments, model organisms |
| `X.forecasting` | forecasting AI progress, timelines, compute trends, scenario work, strategy research without a specific control |
| `X.advocacy-comms` | public communication, journalism, media, campaigns, op-eds, documentaries, outreach to decision-makers that is not a concrete policy control |
| `X.talent-community` | fellowships, courses, career transitions, conferences, hubs, local groups, general support of talent and community organisations |
| `X.none` | none of the above and no MIT control fits (e.g. general support of an organisation whose work you cannot place; nothing about AI) |

## Rules

1. **Choose the MIT control when the grant is about designing, studying, standardising
   or advocating a specific control**: compute governance and licensing → `1.2` or
   `3.3`; safety cases and RSPs → `1.5`; whistleblower protection → `1.4`; model weight
   security → `2.1`; RLHF/constitutional-AI style alignment methods → `2.2`; unlearning,
   filters, capability restriction → `2.3`; watermarking/provenance → `2.4`; evals,
   audits, red-teaming, benchmarks, dangerous-capability evaluations → `3.1`; data
   governance → `3.2`; staged release → `3.4`; monitoring → `3.5`; incident response →
   `3.6`; model cards and documentation → `4.1`; risk disclosure to government → `4.2`;
   incident reporting → `4.3`; governance disclosure → `4.4`; researcher/third-party
   access → `4.5`; user recourse → `4.6`; societal impact assessment → `1.7`;
   environmental footprint → `1.6`; board/oversight structures → `1.1`; conflict of
   interest → `1.3`.
2. **Policy and governance research or advocacy that spans several controls** (general
   AI-policy institutes, "AI governance research", international coordination work)
   → `1.2` if it is about risk-management frameworks and regulation broadly; `X.forecasting`
   if it is strategy/scenario work; `X.advocacy-comms` if it is campaigning.
3. **Research grants**: interpretability → `X.research-interp`; theory/agent foundations
   → `X.research-theory`; other empirical safety research → `X.research-empirical`;
   evaluation and benchmark building → `3.1` (this is a control the taxonomy has).
4. **General support of an organisation** → the method its work mainly is: MIRI →
   `X.research-theory`; Redwood → `X.research-empirical`; METR, Apollo → `3.1`; GovAI,
   IAPS, CLTR → `1.2`; MATS, BlueDot, 80,000 Hours, AI Safety Camp, local hubs →
   `X.talent-community`; Lightcone/LessWrong → `X.talent-community`; FLI → `X.advocacy-comms`;
   Epoch → `X.forecasting`.
5. Confidence: `high` when the text says so, `medium` when you rely on knowing the
   grantee, `low` when guessing. Prefer `X.none` over a guess.

## The 23 MIT control subcategories

**1 Governance & Oversight Controls**
- `1.1` Board Structure & Oversight — executive accountability structures: risk committees, safety teams, ethics boards, deployment veto.
- `1.2` Risk Management — risk-management frameworks, risk registers with capability thresholds, compliance programmes, pre-deployment risk assessment.
- `1.3` Conflict of Interest Protections — stake limits, windfall clauses, protection against shareholder pressure.
- `1.4` Whistleblower Reporting & Protection — confidential reporting channels, non-retaliation.
- `1.5` Safety Decision Frameworks — if-then commitments, capability ceilings, pause triggers, safety/capability resource ratios.
- `1.6` Environmental Impact Management — carbon footprint assessment, energy efficiency.
- `1.7` Societal Impact Assessment — fundamental-rights and societal impact assessment, stakeholder engagement.

**2 Technical & Security Controls**
- `2.1` Model & Infrastructure Security — weight security, access controls, physical security.
- `2.2` Model Alignment — RLHF, DPO, constitutional AI, value alignment verification.
- `2.3` Model Safety Engineering — capability restriction, unlearning, input/output filtering, defence in depth.
- `2.4` Content Safety Controls — watermarking, provenance, content filtering, deepfake restrictions.

**3 Operational Process Controls**
- `3.1` Testing & Auditing — audits, red teaming, penetration testing, dangerous-capability evaluations, bug bounties.
- `3.2` Data Governance — data acquisition/curation policy, privacy controls.
- `3.3` Access Management — KYC, API-only access, fine-tuning restrictions, acceptable-use policy.
- `3.4` Staged Deployment — limited release, gradual expansion, pre-deployment checkpoints.
- `3.5` Post-deployment Monitoring — usage tracking, misuse detection, capability evolution assessment.
- `3.6` Incident Response & Recovery — shutdown/rollback, containment, drills.

**4 Transparency & Accountability Controls**
- `4.1` System Documentation — model cards, architecture and compute disclosure, safety test reports.
- `4.2` Risk Disclosure — risk assessment publication, notifications to government, training-run reporting.
- `4.3` Incident Reporting — incident databases, breach notification, threat-intelligence sharing.
- `4.4` Governance Disclosure — published safety strategies, safety cases, model registration.
- `4.5` Third-Party System Access — researcher access programmes, safe harbours for evaluation.
- `4.6` User Rights & Recourse — reporting channels, appeals, explanations, remediation.

## Output format

CSV with header `grant_id,method,confidence,basis`. `basis` ≤ 10 words, no commas.
