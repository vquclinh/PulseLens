# Pricing Pressure Failure Analysis

Source artifact: `pipeline_audit_artifacts/20260525T171824Z/web_collection_audit.json`

Generated artifact: `pipeline_audit_artifacts/20260526T030015Z/pricing_pressure_failure_analysis.json`

## Summary

The latest full audit had 8 pricing_pressure queries. Four returned zero accepted documents, giving pricing_pressure a 50% zero-doc rate inside a broader pipeline zero-doc rate of 0.537.

Pricing did not become a verified signal because the accepted pricing documents were sparse and not enough pricing facts survived downstream extraction/SAFE/FinBERT into the final scored fact set.

## Main Failure Patterns

- Over-strict `site:` constraints rejected relevant fallback results.
- Several pricing queries targeted companies outside the Sprint 2 demo scope: Dell, HPE, Broadcom, Intel.
- Some queries targeted generic distributor or margin-pressure concepts instead of observable pricing/availability evidence.
- Fallback evaluation reused the original query's strict source/site assumptions even when fallback queries intentionally broadened the search.
- Queries with concrete AI hardware terms worked best: `Nvidia H200 availability distributor` and `AMD MI300X pricing discount`.

## Pricing Query Outcomes

| Query | Company | Docs | Fallback | Likely Cause |
| --- | --- | ---: | --- | --- |
| `q_66ff2f10` | Dell | 0 | yes, no docs | Outside demo scope; too narrowly pinned to `insight.com`. |
| `q_8fc3e229` | HPE | 0 | yes, no docs | Original `site:aws.amazon.com` constraint rejected fallback news/context results. |
| `q_976dc028` | Supermicro | 0 | yes, no docs | `site:cdw.com` rejected relevant Supermicro-owned store/product URLs. |
| `q_a1f2e45d` | Broadcom | 0 | yes, no docs | Outside demo scope; margin-pressure query lacked concrete pricing/availability source path. |
| `q_e994a7b7` | Nvidia | 1 | no | Partially worked, but generic distributor pages were noisy. |
| `q_14f61ce4` | Intel | 2 | yes, docs | Worked somewhat, but outside demo scope. |
| `q_3064ab42` | AMD | 4 | no | Good shape: concrete `MI300X` term plus OEM/server context. |
| `q_e1649fc1` | Nvidia | 4 | no | Good shape: concrete `H200` term plus availability/distributor context. |

## Sprint 2 Implication

Pricing retrieval should be deterministic for the demo companies instead of relying only on LLM query generation. The playbook should use concrete GPU/server terms, cloud pricing domains, and availability/lead-time language, while avoiding over-strict site filters unless the source domain is explicitly part of the playbook.
