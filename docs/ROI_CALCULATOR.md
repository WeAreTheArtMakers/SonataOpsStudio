# ROI Calculator Template

## Inputs
| Metric | Baseline | After SonataOps | Delta | Notes |
|---|---:|---:|---:|---|
| Incident triage time (hours/week) |  |  |  | |
| MTTR (minutes) |  |  |  | |
| Exec report prep time (hours/week) |  |  |  | |
| Missed anomaly escalations/month |  |  |  | |
| Analyst context-switch events/day |  |  |  | |

## Financial Model
| Component | Formula | Value |
|---|---|---:|
| Weekly time saved (hours) | triage savings + report savings | |
| Weekly labor savings ($) | hours saved * blended hourly rate | |
| MTTR impact ($/week) | avoided outage mins * cost per outage min | |
| Total weekly value ($) | labor savings + MTTR impact | |
| Annual value ($) | weekly value * 52 | |

## Payback
| Item | Value |
|---|---:|
| Implementation cost ($) | |
| Annual support cost ($) | |
| Annual value ($) | |
| Payback period (months) | (implementation + annual support) / (annual value / 12) |

## Guidance
- Use conservative estimates in stakeholder-facing ROI narratives.
- Separate hard-dollar savings from soft productivity gains.
