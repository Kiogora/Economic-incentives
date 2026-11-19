"""Uganda clean cooking fiscal incentive simulator — transparent prototype.

This model intentionally does not reproduce the uploaded Excel workbook's formulas.
Its assumptions are illustrative and must be calibrated before policy use.
"""
from __future__ import annotations

import io
import json
import math
import zipfile

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Clean Cooking | Fiscal Incentives", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")

STAGES = ("Early stage", "Mid-stage")
TECHS = ("Ethanol", "LPG", "Electricity", "Biogas", "Biomass")

# All rates are percentages. Defaults below are illustrative, NOT official tax rates.
TAX_COLS = ["Technology", "Import duty (%)", "VAT (%)", "Infrastructure levy (%)", "Withholding (%)"]
DYN_COLS = ["Technology", "Units / firm / year", "Selling price (USD/unit)", "Imported appliance share (%)", "Baseline imported share (%)", "Taxable imported cost / price (%)", "Net profit margin (%)", "Workers / firm", "Annual wage (USD)", "Demand uplift from incentives (%)", "Additional workers / firm", "Additional net margin (pp)"]


def default_tax(stage: str) -> pd.DataFrame:
    rows = []
    for t in TECHS:
        rows.append({"Technology": t, "Import duty (%)": 10.0 if stage == "Early stage" else 7.0,
                     "VAT (%)": 0.0 if stage == "Early stage" else 5.0,
                     "Infrastructure levy (%)": 0.0, "Withholding (%)": 0.0})
    return pd.DataFrame(rows, columns=TAX_COLS)


def baseline_tax() -> pd.DataFrame:
    return pd.DataFrame([{"Technology": t, "Import duty (%)": 10.0, "VAT (%)": 18.0,
                          "Infrastructure levy (%)": 1.5, "Withholding (%)": 0.0} for t in TECHS], columns=TAX_COLS)


def default_dyn(stage: str) -> pd.DataFrame:
    if stage == "Early stage":
        units, jobs, uplift, imported, addjobs, margin = 1100, 5, 12.0, 85.0, 0, 10.0
    else:
        units, jobs, uplift, imported, addjobs, margin = 3000, 14, 85.0, 40.0, 12, 14.0
    prices = {"Ethanol": 55, "LPG": 80, "Electricity": 110, "Biogas": 160, "Biomass": 45}
    return pd.DataFrame([{"Technology": t, "Units / firm / year": units,
                          "Selling price (USD/unit)": prices[t],
                          "Imported appliance share (%)": imported,
                          "Baseline imported share (%)": 85.0,
                          "Taxable imported cost / price (%)": 60.0,
                          "Net profit margin (%)": margin, "Workers / firm": jobs,
                          "Annual wage (USD)": 1800.0,
                          "Demand uplift from incentives (%)": uplift,
                          "Additional workers / firm": addjobs,
                          "Additional net margin (pp)": 0.0}
                         for t in TECHS], columns=DYN_COLS)


def default_industry() -> pd.DataFrame:
    return pd.DataFrame([
        {"Stage": "Early stage", "Duration (years)": 5, "Firms": 15,
         "Annual sales growth (%)": 3.0, "Counterfactual firms (%)": 100.0},
        {"Stage": "Mid-stage", "Duration (years)": 7, "Firms": 50,
         "Annual sales growth (%)": 7.0, "Counterfactual firms (%)": 65.0},
    ])


def validate_table(df: pd.DataFrame, name: str, expected_techs=TECHS) -> None:
    if df.empty or df["Technology"].isna().any():
        raise ValueError(f"{name}: no technology may be blank.")
    if list(df["Technology"]) != list(expected_techs):
        raise ValueError(f"{name}: keep the five technology rows in the supplied order.")
    for col in df.columns:
        if col == "Technology":
            continue
        vals = pd.to_numeric(df[col], errors="coerce")
        if vals.isna().any() or not np.isfinite(vals.to_numpy(dtype=float)).all():
            raise ValueError(f"{name}: {col} contains an invalid or missing number.")
        if (vals < 0).any() and col != "Additional net margin (pp)":
            raise ValueError(f"{name}: {col} cannot be negative.")
        if "(%)" in col and (vals > 100).any():
            raise ValueError(f"{name}: {col} must be at most 100%.")
        if col == "Additional net margin (pp)" and (vals < -100).any():
            raise ValueError(f"{name}: additional net margin cannot be less than -100 percentage points.")


def get_editor_config(df: pd.DataFrame, disabled_cols: list[str]) -> dict:
    cfg = {"Technology": st.column_config.TextColumn("Technology", disabled=True)}
    for col in df.columns:
        if col in ("Technology", "Stage"):
            continue
        cfg[col] = st.column_config.NumberColumn(col, min_value=(None if col == "Additional net margin (pp)" else 0.0), format="%.1f" if "(%)" in col or "(pp)" in col else "%.0f")
    return cfg


def calc_year(stage: str, period: int, year: int, stage_cfg: dict,
              dyn: pd.DataFrame, baseline_rates: pd.DataFrame, policy_rates: pd.DataFrame,
              cit_rate: float, paye_rate: float, demand_cap: float) -> tuple[dict, list[dict]]:
    firms = float(stage_cfg["Firms"])
    counterfactual_firms = firms * float(stage_cfg["Counterfactual firms (%)"]) / 100.0
    growth_multiplier = (1 + float(stage_cfg["Annual sales growth (%)"]) / 100.0) ** period
    base_tax = baseline_rates.set_index("Technology")
    incent_tax = policy_rates.set_index("Technology")
    details = []
    totals = {"Baseline appliance taxes": 0.0, "Policy appliance taxes": 0.0,
              "Baseline PAYE": 0.0, "Policy PAYE": 0.0,
              "Baseline CIT": 0.0, "Policy CIT": 0.0, "Baseline sales (units)": 0.0,
              "Policy sales (units)": 0.0, "Baseline jobs": 0.0, "Policy jobs": 0.0}

    for _, item in dyn.iterrows():
        t = item["Technology"]
        base_units = counterfactual_firms * float(item["Units / firm / year"]) * growth_multiplier
        # Policy sales reflect user-specified additional demand, but are capped by potential demand if provided.
        units = firms * float(item["Units / firm / year"]) * growth_multiplier * (1 + float(item["Demand uplift from incentives (%)"]) / 100)
        if demand_cap > 0:
            # Cap is technology-specific annual demand ceiling, shared across firms.
            base_units = min(base_units, demand_cap)
            units = min(units, demand_cap)
        price = float(item["Selling price (USD/unit)"])
        import_share = float(item["Imported appliance share (%)"]) / 100
        base_import_share = float(item["Baseline imported share (%)"]) / 100
        taxable_import_share = float(item["Taxable imported cost / price (%)"]) / 100
        import_tax_base = price * import_share * taxable_import_share
        baseline_import_tax_base = price * base_import_share * taxable_import_share
        # Simplified gross revenue proxy: import taxes on import value + VAT on final sales price.
        # Withholding treated as retained revenue ONLY for illustrative modelling; remove if creditable/refundable.
        def per_unit_taxes(rate_row, imported_cost_base) -> float:
            r = lambda c: float(rate_row[c]) / 100.0
            return imported_cost_base * (r("Import duty (%)") + r("Infrastructure levy (%)") + r("Withholding (%)")) + price * r("VAT (%)")
        base_appliance_tax = base_units * per_unit_taxes(base_tax.loc[t], baseline_import_tax_base)
        policy_appliance_tax = units * per_unit_taxes(incent_tax.loc[t], import_tax_base)
        workers = float(item["Workers / firm"])
        added = float(item["Additional workers / firm"])
        wage = float(item["Annual wage (USD)"])
        baseline_jobs = counterfactual_firms * workers
        policy_jobs = firms * (workers + added)
        base_paye = baseline_jobs * wage * paye_rate / 100.0
        policy_paye = policy_jobs * wage * paye_rate / 100.0
        margin = float(item["Net profit margin (%)"]) / 100.0
        policy_margin = max(0.0, margin + float(item["Additional net margin (pp)"]) / 100.0)
        base_cit = base_units * price * margin * cit_rate / 100.0
        policy_cit = units * price * policy_margin * cit_rate / 100.0
        chunk = {"Year": year, "Stage": stage, "Technology": t,
                 "Baseline appliance taxes": base_appliance_tax, "Policy appliance taxes": policy_appliance_tax,
                 "Baseline PAYE": base_paye, "Policy PAYE": policy_paye,
                 "Baseline CIT": base_cit, "Policy CIT": policy_cit,
                 "Baseline sales (units)": base_units, "Policy sales (units)": units,
                 "Baseline jobs": baseline_jobs, "Policy jobs": policy_jobs}
        details.append(chunk)
        for k in totals:
            totals[k] += chunk[k]

    rev_base = sum(totals[k] for k in ("Baseline appliance taxes", "Baseline PAYE", "Baseline CIT"))
    rev_policy = sum(totals[k] for k in ("Policy appliance taxes", "Policy PAYE", "Policy CIT"))
    result = {"Year": year, "Stage": stage, **totals,
              "Baseline government revenue": rev_base, "Policy government revenue": rev_policy,
              "Net incremental fiscal revenue": rev_policy - rev_base,
              "Appliance tax difference": totals["Policy appliance taxes"]-totals["Baseline appliance taxes"],
              "PAYE difference": totals["Policy PAYE"]-totals["Baseline PAYE"],
              "CIT difference": totals["Policy CIT"]-totals["Baseline CIT"]}
    return result, details


def simulate(industry: pd.DataFrame, taxes: dict, dynamics: dict, reference: pd.DataFrame,
             cit_rate: float, paye_rate: float, demand_cap: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    yearly, detail = [], []
    yr = 1
    for stage in STAGES:
        stage_row = industry.loc[industry["Stage"] == stage].iloc[0].to_dict()
        for period in range(int(stage_row["Duration (years)"])):
            row, technology_rows = calc_year(stage, period, yr, stage_row, dynamics[stage], reference,
                                             taxes[stage], cit_rate, paye_rate, demand_cap)
            yearly.append(row)
            detail.extend(technology_rows)
            yr += 1
    frame = pd.DataFrame(yearly)
    if not frame.empty:
        frame["Cumulative incremental fiscal revenue"] = frame["Net incremental fiscal revenue"].cumsum()
    return frame, pd.DataFrame(detail)


def first_break_even(yearly: pd.DataFrame):
    if yearly.empty:
        return None
    early_duration = sum(yearly["Stage"] == "Early stage")
    if early_duration <= 0:
        return None
    # Recovery means cumulative gains first offset the prior cumulative early-stage losses.
    early_end = yearly.iloc[early_duration - 1]["Cumulative incremental fiscal revenue"]
    if early_end >= 0:
        return None
    recovered = yearly.loc[(yearly["Year"] > early_duration) &
                           (yearly["Cumulative incremental fiscal revenue"] >= 0)]
    return int(recovered.iloc[0]["Year"]) if not recovered.empty else None


def money(x: float) -> str:
    return f"{'−' if x < 0 else ''}US$ {abs(x):,.0f}"


def chart_fiscal(yearly: pd.DataFrame, early_duration: int, break_even: int | None) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[0] + yearly["Year"].tolist(),
                             y=[0.0] + yearly["Cumulative incremental fiscal revenue"].tolist(),
                             name="Cumulative fiscal impact", mode="lines+markers",
                             line=dict(color="#1678BB", width=3), marker=dict(size=8),
                             hovertemplate="Year %{x}<br>Incremental cumulative revenue: US$ %{y:,.0f}<extra></extra>"))
    fig.add_hline(y=0, line_dash="dash", line_color="#888")
    fig.add_vline(x=early_duration + 0.5, line_dash="dash", line_color="#1678BB")
    fig.add_vrect(x0=0, x1=early_duration+0.5, fillcolor="#DAEDF9", opacity=0.22, line_width=0)
    fig.add_vrect(x0=early_duration+0.5, x1=len(yearly)+0.5, fillcolor="#DDF3E9", opacity=0.22, line_width=0)
    fig.add_annotation(x=max(0.5,early_duration/2), y=1.06, xref="x", yref="paper", text="1 · Early stage", showarrow=False, font=dict(size=12))
    fig.add_annotation(x=(len(yearly)+early_duration+0.5)/2, y=1.06, xref="x", yref="paper", text="2 · Mid-stage", showarrow=False, font=dict(size=12))
    if break_even is not None:
        fig.add_annotation(x=break_even, y=float(yearly.loc[yearly["Year"]==break_even,"Cumulative incremental fiscal revenue"].iloc[0]),
                           text="Break-even", arrowhead=2, ax=-35, ay=-55)
    fig.update_layout(xaxis_title="Year / market development stage", yaxis_title="Cumulative incremental revenue (USD)",
                      template="plotly_white", height=440, margin=dict(l=12,r=12,t=55,b=20),
                      showlegend=False, hovermode="x unified")
    fig.update_xaxes(dtick=1, range=[0.5, len(yearly)+0.5])
    return fig


st.markdown("""<style>
.block-container {padding-top:1.2rem; max-width:1250px;}
[data-testid='stMetric'] {background:#f5f7fa;border:1px solid #e5e9ee;padding:12px;border-radius:9px}
@media(max-width:700px){ .block-container {padding-left:0.9rem;padding-right:0.9rem;} }
</style>""", unsafe_allow_html=True)
st.title("🔥 Clean Cooking Fiscal Incentives Simulator")
st.caption("Uganda · Two-stage industry and firm-level fiscal impact · Illustrative modelling assumptions")
st.warning("**Prototype — not policy-ready.** Defaults are illustrative, not verified Ugandan tax rates. This is a new simplified model, not a formula-exact conversion of the Excel workbook. See Methodology and limitations before using results.", icon="⚠️")

if "industry" not in st.session_state:
    st.session_state.industry = default_industry()
    st.session_state.reference = baseline_tax()
    for stage in STAGES:
        st.session_state[f"tax_{stage}"] = default_tax(stage)
        st.session_state[f"dyn_{stage}"] = default_dyn(stage)

with st.sidebar:
    st.header("Scenario settings")
    cit = st.number_input("Corporate income tax (CIT), %", 0.0, 100.0, 30.0, 1.0, help="Simplified effective flat rate. Illustrative default.")
    paye = st.number_input("Effective PAYE rate, %", 0.0, 100.0, 10.0, 1.0, help="Average effective wage tax, not statutory marginal brackets.")
    demand_cap = st.number_input("Annual demand cap / technology (units; 0 = none)", min_value=0, value=0, step=1000)
    st.divider()
    st.info("For mobile editing, expand each section and swipe horizontally across the editable tables.")

config_industry = {
    "Stage": st.column_config.TextColumn("Stage", disabled=True),
    "Duration (years)": st.column_config.NumberColumn("Duration (years)", min_value=1, max_value=50, step=1, format="%d"),
    "Firms": st.column_config.NumberColumn("Firms (in incentive scenario)", min_value=0, step=1, format="%d"),
    "Annual sales growth (%)": st.column_config.NumberColumn("Annual sales growth (%)", min_value=0, max_value=100, format="%.1f"),
    "Counterfactual firms (%)": st.column_config.NumberColumn("Counterfactual firms (%)", min_value=0, max_value=100, format="%.1f"),
}

st.subheader("1 · Industry-level structure")
st.write("Set **how many firms operate in each stage**, how long each stage lasts and the counterfactual market size (percentage of the incentive scenario's firms). Each technology has the same firm count within a stage in this prototype.")
industry = st.data_editor(st.session_state.industry, key="industry_editor", hide_index=True,
                          num_rows="fixed", column_config=config_industry, width="stretch")
st.caption("A stage lasts the specified number of consecutive years. Mid-stage sales start from their own per-firm assumptions, not automatically from the early-stage terminal volume.")

with st.expander("No-incentive tax baseline — edit the comparator", expanded=False):
    st.write("The no-incentive rates apply in **both** stages. The two policy tables below define each stage's alternative rates.")
    reference = st.data_editor(st.session_state.reference, key="baseline_tax_editor", hide_index=True,
                               num_rows="fixed", disabled=["Technology"], width="stretch",
                               column_config=get_editor_config(st.session_state.reference, ["Technology"]))

st.subheader("2 · Phase-specific tax and company tables")
taxes, dynamics = {}, {}
for stage in STAGES:
    with st.expander(f"{stage} · taxes + company dynamics", expanded=(stage == "Early stage")):
        st.markdown("**A. Incentive tax rates — percentages**")
        st.caption("Rates apply to every year of this stage. Import-based levies use an estimated imported-cost base; VAT uses the final selling price.")
        taxes[stage] = st.data_editor(st.session_state[f"tax_{stage}"],
                                      key=f"tax_editor_{stage}", hide_index=True, num_rows="fixed",
                                      disabled=["Technology"], width="stretch",
                                      column_config=get_editor_config(st.session_state[f"tax_{stage}"], ["Technology"]))
        st.markdown("**B. Company dynamics — per firm and technology**")
        st.caption("Baseline: counterfactual firms × units/firm. Incentive: policy firms × units/firm × (1 + demand uplift). Additional workers are policy-only.")
        dynamics[stage] = st.data_editor(st.session_state[f"dyn_{stage}"],
                                         key=f"dyn_editor_{stage}", hide_index=True, num_rows="fixed",
                                         disabled=["Technology"], width="stretch",
                                         column_config=get_editor_config(st.session_state[f"dyn_{stage}"], ["Technology"]))

try:
    if list(industry["Stage"]) != list(STAGES):
        raise ValueError("Keep both market-development stages in their original order.")
    if industry.isna().any().any():
        raise ValueError("Industry settings contain a blank value.")
    if (industry[["Duration (years)", "Firms"]] < 0).any().any() or (industry["Duration (years)"] < 1).any():
        raise ValueError("Each stage requires at least one year and nonnegative firm counts.")
    for c in ("Annual sales growth (%)", "Counterfactual firms (%)"):
        if ((industry[c]<0)|(industry[c]>100)).any():
            raise ValueError(f"{c} must be between 0 and 100.")
    for c in ("Duration (years)", "Firms"):
        if (industry[c] != industry[c].astype(int)).any():
            raise ValueError(f"{c} must contain whole numbers.")
    if industry["Duration (years)"].sum() > 60:
        raise ValueError("Total model length is capped at 60 years.")
    validate_table(reference, "Tax baseline")
    for stage in STAGES:
        validate_table(taxes[stage], f"{stage}: tax rates")
        validate_table(dynamics[stage], f"{stage}: dynamics")
    yearly, detail = simulate(industry, taxes, dynamics, reference, cit, paye, demand_cap)
except (ValueError, KeyError, OverflowError) as e:
    st.error(f"Please correct the inputs: {e}")
    st.stop()

st.subheader("3 · Government revenue outcomes")
last = float(yearly["Cumulative incremental fiscal revenue"].iloc[-1])
early_years = int(industry.iloc[0]["Duration (years)"])
lowest = yearly["Cumulative incremental fiscal revenue"].min()
be = first_break_even(yearly)
a,b,c,d = st.columns(4)
a.metric("Cumulative fiscal impact", money(last))
b.metric("Largest cumulative shortfall", money(lowest) if lowest < 0 else "None")
c.metric("Fiscal break-even", f"Year {be}" if be else "Not reached")
d.metric("Model horizon", f"{len(yearly)} years")
st.plotly_chart(chart_fiscal(yearly, early_years, be), width="stretch")

chart_view = st.radio("Breakdown", ["Annual revenue change by source", "Policy vs baseline revenue", "Annual sales and jobs"], horizontal=True)
if chart_view == "Annual revenue change by source":
    fig = go.Figure()
    for k,label,color in [("Appliance tax difference", "Appliance taxes", "#2b7bb9"),
                          ("PAYE difference", "PAYE", "#28a381"),
                          ("CIT difference", "Corporate income tax", "#e7ab42")]:
        fig.add_bar(x=yearly["Year"], y=yearly[k], name=label, marker_color=color)
    fig.update_layout(barmode="relative", template="plotly_white", yaxis_title="Incremental revenue (USD)",
                      xaxis_title="Year", height=365, margin=dict(l=10,r=10,t=25,b=10))
elif chart_view == "Policy vs baseline revenue":
    fig = go.Figure()
    for k,label in [("Baseline government revenue", "No-incentive baseline"),
                    ("Policy government revenue", "With incentives")]:
        fig.add_scatter(x=yearly["Year"], y=yearly[k], name=label, mode="lines+markers")
    fig.update_layout(template="plotly_white", yaxis_title="Annual modelled tax receipts (USD)",
                      xaxis_title="Year", height=365, margin=dict(l=10,r=10,t=25,b=10))
else:
    fig = go.Figure()
    for k,label in [("Baseline sales (units)", "Baseline stove units"),
                    ("Policy sales (units)", "With incentives: stove units")]:
        fig.add_scatter(x=yearly["Year"], y=yearly[k], name=label, mode="lines+markers")
    fig.update_layout(template="plotly_white", yaxis_title="Annual units", xaxis_title="Year",
                      height=365, margin=dict(l=10,r=10,t=25,b=10))
st.plotly_chart(fig, width="stretch")

st.markdown("**Annual fiscal accounting table**")
show_cols = ["Year", "Stage", "Baseline government revenue", "Policy government revenue",
             "Appliance tax difference", "PAYE difference", "CIT difference",
             "Net incremental fiscal revenue", "Cumulative incremental fiscal revenue"]
st.dataframe(yearly[show_cols].style.format({c:"{:,.0f}" for c in show_cols if c not in ("Year","Stage")}),
             hide_index=True, width="stretch")

st.markdown("**By-technology comparison**")
summary = detail.groupby(["Stage", "Technology"], as_index=False).sum(numeric_only=True)
summary["Baseline revenue"] = summary[["Baseline appliance taxes","Baseline PAYE","Baseline CIT"]].sum(axis=1)
summary["Policy revenue"] = summary[["Policy appliance taxes","Policy PAYE","Policy CIT"]].sum(axis=1)
summary["Fiscal difference"] = summary["Policy revenue"] - summary["Baseline revenue"]
st.dataframe(summary[["Stage","Technology","Baseline revenue","Policy revenue","Fiscal difference"]].style.format({c:"{:,.0f}" for c in ("Baseline revenue","Policy revenue","Fiscal difference")}),
             hide_index=True, width="stretch")

st.subheader("4 · Export scenario")
scenario = {"industry":industry.to_dict(orient="records"),"baseline_tax":reference.to_dict(orient="records"),
            "stage_taxes":{s:taxes[s].to_dict(orient="records") for s in STAGES},
            "stage_dynamics":{s:dynamics[s].to_dict(orient="records") for s in STAGES},
            "cit_rate":cit,"paye_rate":paye,"annual_demand_cap":demand_cap}
left,right = st.columns(2)
with left:
    st.download_button("⬇️ Download scenario (.json)", json.dumps(scenario, indent=2),
                       file_name="clean_cooking_scenario.json", mime="application/json", width="stretch")
with right:
    csv = yearly.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download annual results (.csv)",csv,file_name="fiscal_results.csv",mime="text/csv",width="stretch")
with st.expander("Methodology, fiscal equations and limitations"):
    st.markdown(r"""
### What is calculated
For each stage, technology and year, the app computes two scenarios using identical output structure:

- **No-incentive baseline:** `counterfactual firms × units/firm/year × (1 + annual sales growth) ^ years within stage`.
- **Incentive scenario:** `policy firms × units/firm/year × (1 + annual sales growth) ^ years within stage × (1 + demand uplift)`.
- **Import tax base per stove:** `selling price × imported appliance share × taxable imported cost / selling price`.
- **Appliance tax revenue:** `units × [scenario-specific import tax base × (duty + infrastructure levy + withholding) + selling price × VAT]`.
- **PAYE:** `firms × (base workers/firm + policy-only additional workers/firm) × annual wage × effective PAYE`.
- **CIT:** `units × price × net profit margin × effective CIT rate` (nonnegative policy margin).
- **Net incremental government revenue:** `(tax + PAYE + CIT with incentives) − (tax + PAYE + CIT without incentives)`.
- **Cumulative fiscal impact:** Sum of yearly incremental revenue, from year 1 onward. Break-even occurs when cumulative losses at the end of the early stage have been fully recovered.

### Important limitations
1. **Illustrative tax accounting:** In real tax law VAT, withholding tax, input credits, and levy bases are not necessarily additive. Withholding is sometimes creditable rather than an incremental final government receipt. Confirm fiscal incidence and VAT input-credit treatment with URA and the workbook before policy use.
2. **No explicit fuel consumption or fuel-tax stream.** The taxes here are for cooking appliances; a fuel-tax module must be added if fuel exemptions are included in the assessment.
3. **Profit margin is an assumed taxable-profit proxy, not a full CIT computation.** Loss carryforwards, thresholds, capital allowances and tax holidays are omitted.
4. **Sales uplift, local employment and counterfactual firm counts are user-specified assumptions; the model does not estimate behavioural demand elasticities or causal effects.**
5. **New model, not an Excel recalculation.** Uploaded workbook has formulas and assumptions relevant to this tool, but this prototype has not replicated or independently audited its complete computation chain.
6. **No inflation, discounting, entry/exit, firm persistence, technology switching, carbon finance or macroeconomic feedback.** Stage 2 assumptions replace stage 1 levels and reset the within-stage growth clock.
7. **Potential demand cap** applies separately to each technology and each year and is shared across firms.
8. **A firm's headcount is multiplied by the number of firms, per technology.** If a single firm sells multiple technologies, counts may double-count staff. For multi-technology firms, use technology-specific full-time-equivalent allocation.

**Units:** Prices, wages and revenues are shown in nominal US dollars. Model timings are relative years, not calendar dates.
""")
st.caption("EED Advisory | Demonstration interface. Validate the model with the project team before external publication.")
