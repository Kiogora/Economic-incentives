# Clean Cooking Fiscal Incentives Simulator — simplified edition

## What changed

- Removed **extra sales with incentives**, **sales without incentives**, **firms without incentives**, **workers without incentives**, **stoves made in Uganda (%)**, **local content (%)**, **extra local sourcing cost (%)**, and **annual stove demand**.
- Kept **Baseline / Early stage / Mid-stage** tax tabs and **Early stage / Mid-stage** company tabs.
- Technology columns are **Ethanol, LPG, Electricity, Biogas, Biomass**. Sliders sit within the tables; a phone view shows one technology at a time.
- Main sidebar controls: **UGX/USD exchange rate, annual wages, CIT, PAYE and first year**.
- Government **CIT and PAYE are separately reported**. Import taxes and VAT are used to calculate company cost or estimated tax relief, not described as CIT/PAYE.

## How the Excel model is arranged

Source: `260826_Economic_Incentives_Final model_V2.xlsm`.

- **Taxes and levies / Assumptions and variables** hold tax and business inputs.
- **Early-stage unit effects and firm effects** link stove imports to firm costs, annual sales, wages and taxes.
- **Mid-stage unit effects and firm effects** describe the next stage of market development.
- **Industry effects** aggregate firms and duration across technologies.

This app is a **simplified interpretation**, not a complete or independently audited formula-by-formula copy of the workbook. Early/mid stages represent consecutive phases for each technology. Each phase's annual stove sales and staffing are supplied explicitly; the app does not invent additional demand caused by tax relief.

## Calculation flow

1. Imported unit cost × annual stove sales × number of firms.
2. Add distribution, other costs, fixed company costs, employee wages, import duty and infrastructure levy.
3. Selling price before VAT = total cost ÷ (1 − target profit margin).
4. Pre-CIT profit = selling revenue − total company costs; **CIT** = profit × CIT rate.
5. Wage bill = workers per firm × number of firms × annual wages; **PAYE** = wage bill × effective PAYE rate.
6. Illustrative tax relief = difference between baseline and incentive duty/levy on import value, plus a simplified gross VAT relief estimate on sales.
7. Illustrative fiscal contribution = **CIT + PAYE − tax relief**.

**Interpretation:** The fiscal contribution is not a causal comparison of two market outcomes, because no changes in sales or employment are attributed to the incentives. A positive result is not proof that the incentives generated net public revenue. Withholding tax is shown for reference but not counted as additional CIT/PAYE receipts.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

To deploy, push `app.py`, `model.py`, and `requirements.txt` to GitHub and select the repository in Streamlit Community Cloud.

## Verification needed before policy use

- Compare all tax bases and expense definitions to source workbook.
- Replace effective PAYE with statutory payroll schedule if precision is required.
- Apply proper import VAT / domestic VAT recoverability, input credits and refund treatment.
- Incorporate CIT deductions, losses, depreciation, and withholding tax credit mechanics.
- Confirm which imported parts costs replace finished stove costs in mid-stage.

## Version 6 — demonstration of fiscal recovery

The default **early stage** uses VAT relief (VAT 0% versus baseline 18%). The
**mid-stage** demonstration increases annual stove sales and staff numbers while
keeping the profit margin at **40%**. It also assumes a partial return of VAT to
**9%** (18% no-incentive baseline). That mid-stage tax assumption is a scenario
choice, not a representation of Uganda's current tax law or a value confirmed
from the workbook. It is essential to the default crossing: with full VAT relief
continuing through the mid-stage, merely increasing sales and workers did not
reverse the cumulative shortfall under this simplified calculation.

**Driving inputs** are editable in the company tables and left-hand sidebar.
**Driven outputs** appear immediately below each stage's company table in a
read-only results table, including annual wages, sale revenue, selling price,
profit, PAYE and CIT per firm. The industry dashboard then multiplies each
company's results by the number of firms and years active in that stage.

With the included illustrative defaults (not empirical projections), the
cumulative fiscal-contribution line crosses zero in 2035. This is not a
causal estimate of fiscal gains attributable to incentives, and does not
replace a properly specified baseline scenario or a reviewed tax model.
