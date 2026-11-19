"""Conference-ready interactive demonstrator; calculations remain illustrative and require validation."""
from __future__ import annotations
import io, json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from model import TECHS, TAX_NAMES, COMPANY_NAMES, INDUSTRY_NAMES, Settings, defaults, simulate

st.set_page_config(page_title='Uganda Clean Cooking | Fiscal Incentives',page_icon='🔥',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
.block-container {padding-top:1.35rem;max-width:1500px}
[data-testid="stMetric"] {border:1px solid #dedee7;border-radius:12px;padding:12px 14px}
[data-testid="stSidebar"] {background:#f8f9fc}
.section-note {color:#606a7a;font-size:.93rem}
.cell-header {font-size:.81rem;font-weight:700;color:#38475b;padding:.3rem 0}
.row-label {padding-top:.65rem;font-size:.86rem;font-weight:600;line-height:1.1}
.tiny {font-size:.78rem;color:#657083}
hr {border-color:#e7e8ed}
[data-testid="stSlider"] {padding-top:0;padding-bottom:0}
</style>''',unsafe_allow_html=True)

if 'model_tables' not in st.session_state:
    st.session_state.model_tables=defaults()
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter=0

st.title('Clean Cooking Fiscal Incentives Simulator')
st.caption('Uganda · EED Advisory · Interactive conference demonstration')
st.markdown('Change a slider **inside any table** to update the government revenue figures and charts. Every amount displayed is in **Uganda shillings (UGX)** unless marked USD. On a phone, turn on **Phone-friendly table view** in the left panel.')

with st.sidebar:
    st.subheader('Main assumptions')
    st.caption('These apply to all five clean cooking technologies.')
    fx=st.number_input('Exchange rate (UGX per USD)',min_value=1.0,max_value=20000.0,value=3505.0,step=10.0,help='The source Excel workbook uses UGX 3,505 per USD. Changing this converts the USD cost assumptions into UGX.')
    start_year=st.number_input('First year',min_value=2020,max_value=2100,value=2027,step=1)
    wage=st.number_input('Annual wages per worker (UGX)',min_value=0.0,max_value=300000000.0,value=3120000.0,step=120000.0,help='From the workbook: UGX 260,000 per worker per month × 12.')
    cit=st.slider('Company income tax – CIT (%)',0,50,30,1)
    paye=st.slider('Employee income tax – PAYE (%)',0,50,25,1)
    st.divider()
    st.caption('**Presentation controls**')
    show_tech=st.multiselect('Show technologies',list(TECHS),default=list(TECHS))
    phone_mode=st.checkbox('Phone-friendly table view',value=False,help='Show one technology at a time, with its sliders beside the row names. Leave off for the Excel-style five-column view.')
    phone_tech=st.selectbox('Technology to edit on phone',list(TECHS)) if phone_mode else None
    if st.button('Reset all tables',use_container_width=True):
        st.session_state.model_tables=defaults()
        st.session_state.reset_counter+=1
        st.rerun()
    st.caption('Inputs from the spreadsheet are starting points, not official policy rates. Confirm tax bases and assumptions before policy decisions.')

config=Settings(fx=fx,wage_ugx=wage, cit_pct=cit,paye_pct=paye,start_year=start_year)

# Monetary cells are edited as UGX, but saved in USD to preserve stable inputs when FX changes.
# In-table sliders are native Streamlit controls, not a detached sensitivity panel.
def show_slider_table(table_name,title,rows,kind):
    table=st.session_state.model_tables[table_name]
    st.markdown(f'**{title}**')
    st.caption('Move any slider. The value shown above each slider is the current input. Percentages are 0–100.')
    active_techs=[phone_tech] if phone_mode else list(TECHS)
    sizes=[2.6]+[1]*len(active_techs)
    header=st.columns(sizes,gap='small')
    with header[0]: st.markdown('<span class="cell-header">Assumption</span>',unsafe_allow_html=True)
    for j,tech in enumerate(active_techs):
        with header[j+1]: st.markdown(f'<span class="cell-header">{tech}</span>',unsafe_allow_html=True)
    for row_i,row_name in enumerate(rows):
        cols=st.columns(sizes,gap='small',vertical_alignment='center')
        with cols[0]:
            st.markdown(f'<div class="row-label">{row_name.replace(" (USD/unit)"," (UGX/stove)").replace(" (USD/firm)"," (UGX/firm)")}</div>',unsafe_allow_html=True)
        for j,tech in enumerate(active_techs):
            raw=float(table.at[row_name,tech]); ismoney='(USD/' in row_name
            value=raw*fx if ismoney else raw
            ispercent='(%)' in row_name
            isint=(not ismoney and not ispercent)
            if ispercent:
                maxval=94.0 if row_name=='Profit margin (%)' else 100.0
                step=.5
            elif ismoney:
                maxval=max(1000.,value*3,5000.)
                step=max(100.,round(max(value,1000.)/1000)*10)
            else:
                maxval=max(100.,value*3,1000. if 'sales' in row_name.lower() or 'demand' in row_name.lower() else 100.)
                step=1.
            with cols[j+1]:
                new=st.slider(f'{row_name} — {tech}',min_value=0.0,max_value=float(maxval),
                    value=float(min(value,maxval)),step=float(step),
                    key=f'{st.session_state.reset_counter}:{table_name}:{row_i}:{tech}:{fx if ismoney else 0}',
                    label_visibility='collapsed',help=f'{tech}: {row_name}')
                st.caption(f'{new:,.0f}' if (ismoney or isint) else f'{new:,.1f}%')
                table.at[row_name,tech]=(new/fx if ismoney else new)
    st.session_state.model_tables[table_name]=table
    with st.expander('See all input values as a spreadsheet-style table'):
        output=table.loc[list(rows)].copy()
        for ix in output.index:
            if '(USD/' in ix:
                output.loc[ix]=output.loc[ix]*fx
                output.rename(index={ix:ix.replace('(USD/unit)','(UGX/stove)').replace('(USD/firm)','(UGX/firm)')},inplace=True)
        st.dataframe(output.style.format('{:,.0f}'),use_container_width=True)

st.subheader('1. How the Excel model works')
with st.expander('Show explanation for conference participants',expanded=True):
    st.markdown('''The original **260826 Economic Incentives Final Model V2.xlsm** examines the clean cooking market in two stages:

- **Early stage:** Businesses mainly sell imported stoves. The model compares taxes before and after incentives, then considers annual stove sales, company costs, workers and taxes paid.
- **Mid-stage:** More stoves are assembled or made in Uganda. The model considers imported parts, local inputs, manufacturing costs, workers and additional taxes.
- **Industry effects:** The model combines the five technologies, numbers of firms and how long incentives apply to estimate the effect on government revenue over time.

The Excel workbook includes **Taxes and levies**, **Assumptions and variables**, **Early stage – unit effects**, **Early stage – Firm effects**, **Mid stage – unit effects**, **Mid stage – Firm effects**, and **Industry effects**. This web application follows that arrangement but makes the inputs easier to explore on a phone or conference screen.

**How to read the results:** Government revenue *with incentives* minus revenue *without incentives* is the annual change. Adding that change over time gives the cumulative government revenue trend. A negative number means less tax revenue than the baseline; a positive number means more.''')
    st.warning('**Model status:** This is an interactive adaptation, not an audited Excel-to-Python conversion. It uses some original workbook inputs and some clearly identified demonstration assumptions. VAT, PAYE, CIT, input credits and tax losses are simplified. The displayed values are scenarios, not forecasts or official revenue estimates.',icon='⚠️')

st.subheader('2. Industry settings')
st.caption('Choose how many businesses participate in each stage, how long each stage lasts and how quickly annual stove sales grow.')
show_slider_table('industry','Business numbers and incentive years',INDUSTRY_NAMES,'industry')

st.subheader('3. Tax rates')
st.caption('Baseline = without new incentives. Early stage and mid-stage = taxes after the proposed changes.')
tax_tabs=st.tabs(['Baseline','Early stage','Mid-stage'])
for tab,key,heading in zip(tax_tabs,['tax_baseline','tax_early','tax_mid'],['Taxes without incentives','Taxes in the early stage','Taxes in the mid-stage']):
    with tab:
        show_slider_table(key,heading,TAX_NAMES,'tax')

st.subheader('4. Company dynamics')
st.caption('Start with imported stove cost, add taxes and company expenses, then apply a profit margin. Annual stove sales determine how much the business sells.')
co_tabs=st.tabs(['Early stage','Mid-stage'])
for tab,key,heading in zip(co_tabs,['company_early','company_mid'],['Early stage – stove sales, costs and workers','Mid-stage – local production, sales, costs and workers']):
    with tab:
        st.info('Costs from the original workbook are denominated in USD and converted to UGX using the exchange rate on the left. Wages, PAYE and CIT come from the left panel.')
        show_slider_table(key,heading,COMPANY_NAMES,'company')

try:
    annual,details=simulate(st.session_state.model_tables,config)
except (AssertionError,ValueError,OverflowError) as exc:
    st.error(f'Please check your assumptions: {exc}')
    st.stop()
if annual.empty:
    st.warning('Enter at least one year of incentives to calculate results.')
    st.stop()

st.subheader('5. Government revenue results')
st.caption('All values in UGX. Change in revenue = tax receipts with incentives minus tax receipts without incentives.')
net=float(annual['Cumulative change (UGX)'].iloc[-1]);policy=float(annual['Government revenue with incentives (UGX)'].sum())
first_neg=annual[annual['Cumulative change (UGX)']<0]
if not first_neg.empty:
    later=annual[(annual['Year']>first_neg['Year'].iloc[0])&(annual['Cumulative change (UGX)']>=0)]
    breakeven=str(int(later.iloc[0]['Year'])) if not later.empty else 'Not reached'
else: breakeven='No initial loss'
a,b,c=st.columns(3)
a.metric('Cumulative change in revenue',f'UGX {net:,.0f}')
b.metric('Total tax collected with incentives',f'UGX {policy:,.0f}')
c.metric('Year losses are recovered',breakeven)

fig=go.Figure()
fig.add_trace(go.Scatter(x=[start_year-1]+annual['Year'].tolist(),y=[0]+annual['Cumulative change (UGX)'].tolist(),mode='lines+markers',name='Cumulative change',line=dict(color='#136a9c',width=3)))
fig.add_hline(y=0,line_dash='dash',line_color='#777')
phase_end=int(st.session_state.model_tables['industry'].loc['Early stage (years)'].max())
if phase_end: fig.add_vline(x=start_year+phase_end-.5,line_dash='dash',line_color='#e88c32',annotation_text='Last early stage ends')
if breakeven.isnumeric():
    row=annual[annual['Year']==int(breakeven)].iloc[0]
    fig.add_annotation(x=int(breakeven),y=float(row['Cumulative change (UGX)']),text='Early losses recovered',showarrow=True,ay=-45)
fig.update_layout(height=460,margin=dict(l=10,r=10,t=35,b=15),xaxis_title='Year',yaxis_title='Cumulative change in government revenue (UGX)',hovermode='x unified')
st.plotly_chart(fig,use_container_width=True)

st.subheader('6. Government revenue by technology')
st.caption('Compare ethanol, LPG, electricity, biogas and biomass. Select cumulative or annual figures.')
visible=[x for x in TECHS if x in show_tech]
if visible:
    selection=st.radio('Show',['Cumulative change','Annual change','Total tax collected'],horizontal=True)
    sub=details[details.Technology.isin(visible)].copy()
    frame=(sub.groupby(['Year','Technology'],as_index=False)[['Change in government revenue (UGX)','Government revenue with incentives (UGX)']].sum())
    if selection=='Cumulative change':
        frame['Amount (UGX)']=frame.groupby('Technology')['Change in government revenue (UGX)'].cumsum()
    elif selection=='Annual change':frame['Amount (UGX)']=frame['Change in government revenue (UGX)']
    else:frame['Amount (UGX)']=frame['Government revenue with incentives (UGX)']
    fc=px.line(frame,x='Year',y='Amount (UGX)',color='Technology',markers=True,category_orders={'Technology':list(TECHS)})
    fc.add_hline(y=0,line_dash='dash',line_color='#777')
    fc.update_layout(height=420,margin=dict(l=10,r=10,t=20,b=15))
    st.plotly_chart(fc,use_container_width=True)
    stage_summary=sub.groupby(['Technology','Stage'],as_index=False)[['Government revenue with incentives (UGX)','Government revenue without incentives (UGX)','Change in government revenue (UGX)']].sum()
    st.markdown('**Government revenue by technology and stage (UGX)**')
    st.dataframe(stage_summary.style.format({c:'{:,.0f}' for c in stage_summary.columns if '(UGX)' in c}),hide_index=True,use_container_width=True)
    taxkeys=['Import duty','Infrastructure levy','VAT (simplified)','PAYE','CIT']
    tech_totals=sub.groupby('Technology',as_index=False)[['Change - '+k for k in taxkeys]].sum()
    stacked=go.Figure()
    for k in taxkeys:stacked.add_bar(x=tech_totals['Technology'],y=tech_totals['Change - '+k],name=k)
    stacked.update_layout(barmode='relative',height=390,margin=dict(l=10,r=10,t=25,b=15),yaxis_title='Change in government revenue (UGX)',xaxis_title='Technology')
    st.markdown('**Which taxes explain the change?**')
    st.plotly_chart(stacked,use_container_width=True)
    focus=st.selectbox('Look at one technology',visible)
    d=sub[sub.Technology==focus]
    st.dataframe(d[['Year','Stage','Annual stove sales','Selling price per stove (UGX)',
                   'Government revenue with incentives (UGX)','Government revenue without incentives (UGX)',
                   'Change in government revenue (UGX)']].style.format({c:'{:,.0f}' for c in d.columns if c in [
                    'Annual stove sales','Selling price per stove (UGX)','Government revenue with incentives (UGX)',
                    'Government revenue without incentives (UGX)','Change in government revenue (UGX)']}),hide_index=True,use_container_width=True)
else:st.info('Choose at least one technology from the left panel.')

st.subheader('7. Download results and conference notes')
left,middle,right=st.columns(3)
with left:st.download_button('Annual results (CSV)',annual.to_csv(index=False).encode('utf-8-sig'),file_name='government_revenue_by_year_ugx.csv',mime='text/csv',use_container_width=True)
with middle:st.download_button('Technology results (CSV)',details.to_csv(index=False).encode('utf-8-sig'),file_name='government_revenue_by_technology_ugx.csv',mime='text/csv',use_container_width=True)
with right:
    scenario={'settings':config.__dict__,'source':'260826_Economic_Incentives_Final model_V2.xlsm','status':'Illustrative model adaptation',
              'tables':{k:v.to_dict(orient='index') for k,v in st.session_state.model_tables.items()}}
    st.download_button('Save scenario (JSON)',json.dumps(scenario,indent=2).encode(),file_name='clean_cooking_scenario.json',mime='application/json',use_container_width=True)
with st.expander('Model assumptions and limitations'):
    st.markdown('''**Source workbook:** `260826_Economic_Incentives_Final model_V2.xlsm`. Imported stove CIF costs (USD 20, 40, 45, 2,035, 10), exchange rate UGX 3,505/USD, early-stage annual fixed costs and several sales/worker inputs are taken from its relevant worksheets. Some shipping, growth, counterfactual, and policy rates are demonstration assumptions.

**Simplified tax calculations:** Customs duty and infrastructure levy are calculated on the imported stove CIF value or estimated imported component value. VAT is a simplified gross transaction-tax proxy rather than VAT remitted net of input credits; fuel taxation is not included. Withholding tax is shown separately and excluded from the net government revenue change to avoid possible double counting. PAYE is a single effective rate, not the statutory graduated schedule. CIT ignores depreciation, loss carry-forwards and deductibility nuances.

**Company pricing:** Cost per unit includes imported cost, relevant import charges, shipping, other expenses, wages and allocated fixed costs; a target profit margin determines selling price before VAT. A real market may constrain that selling price. The baseline uses separately editable sales, firm and workforce assumptions; it is not a causal forecast.

**Caution:** All reported results are scenarios for exploring assumptions. Audit the tax law and reconcile calculations with Excel before formal publication or policy recommendations.''')
