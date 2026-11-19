# Uganda Clean Cooking Fiscal Incentives Simulator — conference edition

Interactive Streamlit model for EED Advisory conference demonstrations. It follows the structure of the provided workbook `260826_Economic_Incentives_Final model_V2.xlsm` without claiming to reproduce every formula. **Financial outputs are scenario demonstrations, not audited projections.**

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local address shown in the terminal, generally `http://localhost:8501`. For mobile access, deploy this directory in a GitHub repository via Streamlit Community Cloud. Keep the app non-public if data are confidential.

## Using the app

1. In the left panel, set **Exchange rate (UGX per USD)** (workbook: 3,505), **Annual wages per worker (UGX)** (260,000 UGX/month x 12), **CIT**, **PAYE** and simulation start year.
2. In **Industry settings**, change the number of firms, stage duration and growth for each vertical.
3. In **Tax rates**, use the **Baseline**, **Early stage** and **Mid-stage** tabs. Every technology's input has its slider **inside the table**.
4. In **Company dynamics**, switch between **Early stage** and **Mid-stage**. Technology columns match the Excel model. The slider value for a USD-denominated cost is displayed/edited in UGX. The input is saved in USD internally so changing the exchange rate recomputes UGX values without changing the underlying USD assumptions.
5. View **cumulative government revenue**, then **revenue by technology and tax type**, and export annual and technology CSV data. Save the current assumptions as JSON.

## Workbook mapping

| Excel sheet | Streamlit section |
| --- | --- |
| Taxes and levies | Tax rates: Baseline |
| Assumptions and variables | Sidebar: exchange rate |
| Early stage - unit effects | Early stage stove import costs and tax rates |
| Early stage - Firm effects | Early stage company dynamics |
| Mid stage - unit effects | Mid-stage tax rates, imported parts and local content |
| Mid stage - Firm effects | Mid-stage company dynamics, production employment and margins |
| Industry effects | Firm counts, duration, growth and all-technology revenue curves |

## Calculation sketch

- `CIF cost × imported stoves` → finished-appliance import tax base.
- `CIF cost × locally made stoves × imported-content share` → estimated imported-parts tax base.
- **Company costs** = imported/imported-parts input costs + levies/duties + distribution + other expenses + wages + annual fixed costs.
- **Stove selling price before VAT** = company costs / `(1 - target margin)` / annual stoves sold.
- Government revenue = duty + levy + simplified VAT + effective PAYE + effective CIT. Withholding is available as an informational gross-cash figure only.
- **Change in government revenue** = taxes with incentives - taxes without incentives.
- **Cumulative change** = sum of annual changes.

## Status and limitations

The workbook's tax selector also contains **fuel** duty/VAT/excise rows, which are not modelled in this prototype. VAT is a proxy that does not net input VAT credits. PAYE and CIT are effective-rate approximations, not full Uganda statutory calculations; CIT does not account for losses, deductions, depreciation, and tax incentives beyond the visible rates. This app uses a simplified counterfactual and assumes the chosen company profit margin can be passed through to the selling price. Some base assumptions differ from the spreadsheet and are supplied as scenario starting values. **Do not present the resulting simulated figures as validated tax-revenue forecasts.**

Run tests with:

```bash
python -m unittest discover -s tests -v
```
