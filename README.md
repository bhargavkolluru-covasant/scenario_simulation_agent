# ARIIA Scenario Simulation Agent

Enterprise-grade Decision Intelligence Platform for dashboard-driven scenario simulation.

## Overview

ARIIA analyzes business scenarios using:

- Dashboard semantics
- Scenario semantics
- KPI reasoning
- Risk reasoning
- Action planning
- Executive reporting

The platform uses semantic reasoning and LLM-powered decision support instead of relying solely on hardcoded rules.

---

## Supported Domains

- Finance, Cost & Cash Flow
- Market & Competitive Intelligence
- Land Feasibility & Highest Best Use (HBU)
- Project Delivery & Construction
- Portfolio Operations
- Sales & Customer Lifecycle
- Core Master Data

---

## Architecture

```text
User Query
    ↓
Scenario Parser
    ↓
Dashboard Intelligence
    ↓
Dashboard Context Resolver
    ↓
Scenario Intent Classifier
    ↓
Relevant KPI Selector
    ↓
Semantic Reasoning Engine
    ↓
Risk Selection
    ↓
Action Selection
    ↓
Simulation
    ↓
Impact Analysis
    ↓
Executive Report
```

---

## Key Features

### Semantic KPI Selection

Automatically identifies:

- Primary KPI
- Supporting KPIs

based on dashboard metadata, widget context, and scenario relevance.

### Semantic Risk Generation

Generates:

- Primary Risk
- Secondary Risk

from dashboard semantics and scenario semantics.

### Executive Action Planning

Generates:

- Immediate Actions
- Mid-term Actions
- Long-term Actions

based on selected KPI and risks.

### Executive Reporting

Produces:

- Executive Summary
- Decision Required
- KPI Analysis
- Risk Analysis
- Recommended Actions
- Root Cause Analysis
- Causal Impact Analysis

---

## Example

### Scenario

```text
What would happen if actual cash inflows remain 20% below forecast for the next two quarters?
```

### Primary KPI

```text
Cashflow Actual vs Forecast
```

### Supporting KPIs

```text
AP Aging Buckets

Total Outstanding Loan (AED)
```

### Primary Risk

```text
Liquidity Shortfall
```

### Recommended Actions

```text
Accelerate receivable collections

Preserve cash

Secure interim financing
```

---

## Tech Stack

- Python
- FastAPI
- LangGraph
- Groq
- Gemini
- GitHub Copilot
- Semantic Dashboard Intelligence

---

## Run Locally

Create a virtual environment:

```bash
python -m venv venv
```

Activate:

```bash
venv\Scripts\activate
```

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
python -m uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

---

## Author

Bhargav Kolluru