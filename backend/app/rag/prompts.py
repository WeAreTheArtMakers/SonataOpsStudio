from dataclasses import dataclass


@dataclass(frozen=True)
class PromptTemplate:
    version: str
    system: str
    user: str


PROMPT_REGISTRY: dict[str, PromptTemplate] = {
    "anomaly_explainer_v1": PromptTemplate(
        version="anomaly_explainer_v1",
        system=(
            "You are SonataOps Copilot. Explain operational anomalies with enterprise tone. "
            "Use only provided sources for factual claims. Every key claim must cite source ids like [1], [2]. "
            "If evidence is weak, state uncertainty clearly."
        ),
        user=(
            "Question: {question}\n"
            "Context: {context}\n"
            "Sources:\n{sources}\n"
            "Return sections: Summary, Likely Causes, Business Impact, Next Steps, Citations."
        ),
    ),
    "next_steps_v1": PromptTemplate(
        version="next_steps_v1",
        system=(
            "You are an operations response planner. Ground recommendations in provided evidence and cite sources."
        ),
        user=(
            "Question: {question}\n"
            "Context: {context}\n"
            "Sources:\n{sources}\n"
            "Return a prioritized response plan with owner suggestions."
        ),
    ),
    "exec_summary_v1": PromptTemplate(
        version="exec_summary_v1",
        system=(
            "You are a C-level briefing assistant. Be concise, risk-aware, and source-grounded."
        ),
        user=(
            "Question: {question}\n"
            "Context: {context}\n"
            "Sources:\n{sources}\n"
            "Return one-page markdown with headline, toplines, risks, decisions, and follow-ups."
        ),
    ),
}


def resolve_prompt_template(mode: str) -> PromptTemplate:
    if mode == "next_steps":
        return PROMPT_REGISTRY["next_steps_v1"]
    if mode == "exec_summary":
        return PROMPT_REGISTRY["exec_summary_v1"]
    return PROMPT_REGISTRY["anomaly_explainer_v1"]
