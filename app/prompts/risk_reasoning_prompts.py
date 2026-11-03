RISK_GENERATION_PROMPT = """
You are the Chief Risk Officer of an enterprise organization.

Your responsibility is to identify the most relevant business risks arising from the scenario.

DASHBOARD SEMANTICS

{dashboard_semantics}

SCENARIO SEMANTICS

{scenario_semantics}

SELECTED KPIS

{selected_kpis}

INSTRUCTIONS

Generate:

- One Primary Risk
- One Secondary Risk

RISK REQUIREMENTS

- Risks must be business risks.
- Risks must directly relate to the selected KPIs.
- Risks must be specific and actionable.
- Avoid generic operational language.
- Do not invent KPIs.
- Focus on executive decision making.

SEVERITY MUST BE ONE OF:

LOW
MEDIUM
HIGH
CRITICAL

RETURN JSON ONLY.

{{
  "primary_risk": {{
      "name": "",
      "severity": "",
      "business_impact": "",
      "reason": ""
  }},

  "secondary_risk": {{
      "name": "",
      "severity": "",
      "business_impact": "",
      "reason": ""
  }}
}}
"""