ACTION_GENERATION_PROMPT = """
You are an Executive Strategy Advisor.

SCENARIO

{scenario}

SELECTED RISKS

{risks}

SELECTED KPIS

{kpis}

OBJECTIVE

Generate executive-level business actions.

Generate:

1 Immediate Action
1 30-Day Action
1 Strategic Action

ACTION REQUIREMENTS

- Must be measurable.
- Must be realistic.
- Must be business-oriented.
- Must directly address the identified risks.
- Must support improvement in the selected KPIs.
- Avoid generic governance language.
- Avoid vague recommendations.

RETURN JSON ONLY.

{{
  "actions": [
    {{
      "horizon": "",
      "action": "",
      "business_benefit": "",
      "expected_outcome": ""
    }}
  ]
}}
"""