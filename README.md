# Clean Cooking Fiscal Incentives Simulator

An editable Streamlit web prototype for Uganda's clean cooking industry.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Deploy to phone-accessible website

1. Put `app.py` and `requirements.txt` in a GitHub repository.
2. In Streamlit Community Cloud (https://share.streamlit.io), choose **Create app** and select the repository and `app.py`.
3. Deploy, then open the generated `https://...streamlit.app` URL from a phone.

## Interface

- Industry table: early and mid-stage durations, firms, annual growth, baseline market share.
- Baseline tax table and two separate stage-specific incentive tax tables.
- Two company tables: selling prices, quantities, imported shares, margins, workforce, wages and induced demand.
- Plots: cumulative incremental government revenue, annual tax changes, and baseline-vs-policy revenue.
- Download modelled annual results as CSV and edited assumptions as JSON.

**Important:** Exported scenario JSON is an audit/export record; uploading/importing a saved scenario into the app is not yet implemented. This prototype is not a fully verified conversion of the uploaded workbook and uses illustrative assumptions. No official Uganda fiscal rates are asserted.

## Modelling notes

See the **Methodology, fiscal equations and limitations** expander in the app for definitions, assumptions, and known caveats. Distinguish incremental fiscal revenues from total government tax receipts. Validate VAT crediting and withholding tax treatment before policy use.
