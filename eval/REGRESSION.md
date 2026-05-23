# Regression Failure Log

Use this file to preserve failed evaluation cases and follow-up fixes.

## Template

- Eval run:
- Sample id:
- Question:
- Expected behavior:
- Actual behavior:
- Failure type: retrieval | citation | faithfulness | completeness | refusal | routing | latency
- Root cause:
- Fix:
- Owner:
- Status:

_Last refreshed from `rag_eval_judged_final_20260508_230616.json` on 2026-05-08 23:06 UTC._

## Open Failures
### Sample `policy_004` — policy_qa / medium

- Eval run: `rag_eval_judged_final_20260508_230616.json`
- Question: When should procurement escalate a supplier incident?
- Expected sources: incident_response_sop.txt
- Actual sources (top): incident_response_sop.txt
- Recall@5: True  ·  MRR: 1.0
- Judge scores: faithfulness=4, citation_precision=5, answer_completeness=3, refusal_accuracy=5
- Failure types: completeness
- Root cause hypothesis: expected answer points missing from response
- Fix:
- Owner:
- Status: open

### Sample `policy_012` — policy_qa / medium

- Eval run: `rag_eval_judged_final_20260508_230616.json`
- Question: What should procurement do before approving a non-strategic supplier?
- Expected sources: supplier_onboarding_sop.txt
- Actual sources (top): supplier_policy_demo.txt, procurement_faq.txt, supplier_onboarding_sop.txt
- Recall@5: True  ·  MRR: 0.3333
- Judge scores: faithfulness=3, citation_precision=4, answer_completeness=2, refusal_accuracy=5
- Failure types: faithfulness, completeness
- Root cause hypothesis: expected answer points missing from response
- Fix:
- Owner:
- Status: open

### Sample `policy_019` — policy_qa / easy

- Eval run: `rag_eval_judged_final_20260508_230616.json`
- Question: Can the system answer employee travel policy?
- Expected sources: n/a
- Actual sources (top): supplier_policy_demo.txt, procurement_faq.txt, incident_response_sop.txt
- Recall@5: True  ·  MRR: 0.0
- Judge scores: faithfulness=5, citation_precision=3, answer_completeness=5, refusal_accuracy=5
- Failure types: citation
- Root cause hypothesis: citations did not directly support the answer
- Fix:
- Owner:
- Status: open
