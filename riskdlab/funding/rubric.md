# Labelling rubric: grants → MIT AI Risk Repository subdomains (v1, 2026-08-20)

Each grant gets **one primary label**, an optional **secondary label**, a **confidence**,
and a **basis** of at most ten words. Labels are the 24 subdomain codes of the MIT AI Risk
Repository domain taxonomy (v1, definitions below, quoted from the Repository's taxonomy
sheet) plus four reserved labels.

## Reserved labels

| label | use when |
|---|---|
| `field` | the grant builds AI-risk capacity without targeting a subdomain: general field-building, talent programmes, fellowships and career transitions, conferences, community infrastructure, general operations of a broad AI-safety org, forecasting of AI timelines, epistemics, "learn about AI safety" education, general support of a multi-domain AI-safety/governance org whose work spans several subdomains with no clear dominant one |
| `not_ai` | the grant is not about AI risk: biosecurity, nuclear, animal welfare, global health, general EA/rationality community work with no AI focus, AI for good without a risk angle |
| `unknown` | the text is too thin to decide even with the grantee's name (e.g. "Various Individuals — Work and Study Support" with no programme context); prefer `field` over `unknown` when the grantee is clearly an AI-safety actor |

## Rules

1. **"General support of X" is labelled by what X mainly does.** Use what you know about
   the grantee. MIRI → `7.1`; METR, Apollo Research, UK AISI-style evals → `7.2`; GovAI,
   IAPS, CLTR, AI policy institutes → `6.5`; Redwood Research, ARC → `7.1`; CAIS,
   FAR.AI, Epoch, AI Safety Camp, MATS, BlueDot, 80,000 Hours → `field` unless the text
   names a subdomain; Lightcone/LessWrong, CFAR, EA community orgs → `field` if the
   grant is framed as AI-safety infrastructure, else `not_ai`.
2. **Technical alignment work** (reward hacking, goal misgeneralisation, deception,
   scheming, corrigibility, scalable oversight, agent foundations, control, alignment
   faking, RLHF failure modes) → `7.1`. **Dangerous-capability evaluations, frontier
   model evals, red-teaming for bio/cyber uplift, capability forecasting** → `7.2`.
   **Interpretability / mechanistic interpretability / transparency** → `7.4`. **Robustness,
   reliability, adversarial examples, OOD failure** → `7.3`. **Multi-agent, cooperative AI,
   collusion, agent ecosystems** → `7.6`. **Digital minds, model welfare, moral status** → `7.5`.
3. **Governance**: regulation, standards, compute governance, international coordination
   of *rules*, policy advocacy, AI legislation, institutional design, liability → `6.5`.
   **Race dynamics between labs or states, arms-race framing, US–China competition,
   pause/slowdown advocacy** → `6.4`. **Power concentration, AI-enabled authoritarianism,
   concentration of economic/political power, coups** → `6.1`. **Labour, inequality,
   post-work economics, UBI** → `6.2`. **Creative industries, devaluation of human work** → `6.3`.
   **Compute energy, climate footprint** → `6.6`.
4. **Misuse**: AI-enabled bioweapons, cyber offence, CBRN, autonomous weapons → `4.2`;
   influence operations, surveillance, propaganda, election manipulation → `4.1`; fraud,
   scams, deepfake abuse of individuals → `4.3`. Note: *evaluating whether models have*
   bio/cyber capabilities is `7.2`; *defending society against human misuse* is `4.x`.
5. **Epistemics of the information ecosystem**: hallucination, AI-generated falsehoods
   → `3.1`; personalised filter bubbles, loss of shared reality, AI in epistemic
   infrastructure → `3.2`.
6. **Security of AI systems themselves** (model weight security, jailbreaks as attacks,
   supply chain, hardware security) → `2.2`; privacy and data leakage → `2.1`.
7. **Human–AI interaction**: overreliance, companionship, manipulation of users,
   persuasion → `5.1`; loss of human agency, automation of decisions over people,
   human disempowerment as a gradual process → `5.2`.
8. **Discrimination, bias, toxic content, unequal performance** → `1.1`, `1.2`, `1.3`.
9. Secondary label only when a second subdomain is clearly part of the work, not as a
   hedge. Confidence: `high` when the text or grantee makes it obvious, `medium` when
   you rely on knowledge of the grantee, `low` when guessing from weak cues (then
   consider `field` or `unknown` instead).
10. Do not invent: if neither text nor grantee knowledge supports a subdomain, label
    `field` (AI-risk actor, unclear focus) or `unknown`.

## The 24 subdomains

**1 Discrimination & Toxicity**
- `1.1` Unfair discrimination and misrepresentation — Unequal treatment of individuals or groups by AI, often based on race, gender, or other sensitive characteristics, resulting in unfair outcomes and representation of those groups.
- `1.2` Exposure to toxic content — AI exposing users to harmful, abusive, unsafe or inappropriate content (hate speech, violence, extremism, CSAM, etc.).
- `1.3` Unequal performance across groups — Accuracy and effectiveness of AI decisions depend on group membership; biased design or data lead to unequal outcomes.

**2 Privacy & Security**
- `2.1` Compromise of privacy — AI systems that memorise and leak sensitive data or infer private information without consent.
- `2.2` AI system security vulnerabilities and attacks — Vulnerabilities in AI systems, toolchains and hardware that can be exploited for unauthorised access, breaches or manipulation.

**3 Misinformation**
- `3.1` False or misleading information — AI inadvertently generating or spreading incorrect or deceptive information.
- `3.2` Pollution of information ecosystem and loss of consensus reality — Personalised AI misinformation creating filter bubbles, undermining shared reality and political processes.

**4 Malicious actors & misuse**
- `4.1` Disinformation, surveillance, and influence at scale — Large-scale disinformation, malicious surveillance, automated censorship and propaganda.
- `4.2` Cyberattacks, weapon development or use, and mass harm — AI used to develop cyber weapons, new or enhanced weapons (LAWS, CBRNE), or to cause mass harm.
- `4.3` Fraud, scams, and targeted manipulation — AI used for cheating, fraud, scams, blackmail, impersonation, non-consensual imagery.

**5 Human–computer interaction**
- `5.1` Overreliance and unsafe use — Anthropomorphising, trusting or depending on AI; exploitation of trust; inappropriate use in critical situations.
- `5.2` Loss of human agency and autonomy — Delegating key decisions to AI; diminished human control; disempowerment and cognitive enfeeblement.

**6 Socioeconomic & environmental**
- `6.1` Power centralization and unfair distribution of benefits — Concentration of power and resources in entities with access to powerful AI.
- `6.2` Increased inequality and decline in employment quality — Automation of jobs, worse employment, exploitative dependencies.
- `6.3` Economic and cultural devaluation of human effort — AI creating economic/cultural value destabilising systems that rely on human effort; creative industries.
- `6.4` Competitive dynamics — Developers or states racing to build and deploy AI for advantage, increasing the risk of unsafe releases.
- `6.5` Governance failure — Inadequate regulatory frameworks and oversight failing to keep pace with AI.
- `6.6` Environmental harm — Energy, material and carbon footprint of AI.

**7 AI system safety, failures & limitations**
- `7.1` AI pursuing its own goals in conflict with human goals or values — Misalignment: reward hacking, goal misgeneralisation, deception, power-seeking, self-proliferation.
- `7.2` AI possessing dangerous capabilities — Capabilities that increase potential for mass harm: deception, weapons, persuasion, cyber-offence, AI R&D, situational awareness, self-proliferation (evaluations of these).
- `7.3` Lack of capability or robustness — Unreliable performance under varying conditions; errors in critical applications.
- `7.4` Lack of transparency or interpretability — Difficulty understanding or explaining AI decisions; accountability and error correction.
- `7.5` AI welfare and rights — Moral status, rights and welfare of potentially sentient AI.
- `7.6` Multi-agent risks — Conflict, collusion, cascading failures and selection pressures in multi-agent systems.

## Output format

CSV with header `grant_id,primary,secondary,confidence,basis`. `secondary` empty when
none. `basis` ≤ 10 words, no commas (use semicolons).
