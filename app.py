"""Simple clean cooking fiscal incentives demonstration, Streamlit web app."""
import json
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from model import TECHS,TAX_NAMES,COMPANY_NAMES,INDUSTRY_NAMES,Settings,defaults,simulate,calculate_company

st.set_page_config(page_title='Clean Cooking Tax Incentives',page_icon='🔥',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>.block-container{padding-top:1rem;max-width:1550px}
[data-testid="stSidebar"]{background:#f8fafc}
[data-testid="stMetric"]{border:1px solid #e1e5ec;border-radius:12px;padding:14px}
[data-testid="stSlider"]{padding:0}
</style>''',unsafe_allow_html=True)
if 'tables' not in st.session_state:st.session_state.tables=defaults()
if 'reset_no' not in st.session_state:st.session_state.reset_no=0
st.title('Clean Cooking Tax Incentives Simulator')
st.caption('Uganda · EED Advisory · Change driving inputs to see how stove sales, employment, PAYE and CIT affect government revenue')

with st.sidebar:
    st.header('Main assumptions')
    fx=st.number_input('Exchange rate (UGX per USD)',value=3505.0,min_value=1.0,step=25.0)
    wage=st.number_input('Annual wages per worker (UGX)',value=3120000.0,min_value=0.0,step=120000.0)
    cit=st.slider('CIT (%)',0,50,30)
    paye=st.slider('PAYE (%)',0,50,25)
    year=st.number_input('First year',min_value=2020,max_value=2100,value=2027)
    st.divider()
    phone=st.toggle('Phone view: edit one technology',value=False)
    technology=st.selectbox('Technology',TECHS) if phone else None
    if st.button('Reset inputs',use_container_width=True):
        st.session_state.tables=defaults();st.session_state.reset_no+=1;st.rerun()

settings=Settings(fx=fx,wage_ugx=wage,paye_pct=paye,cit_pct=cit,start_year=int(year))

# Sliders are embedded in the same grid as the row names and technology columns.
def input_table(key,rows):
    tab=st.session_state.tables[key]
    techs=[technology] if phone else list(TECHS)
    widths=[2.35]+[1]*len(techs)
    header=st.columns(widths)
    header[0].markdown('**Input**')
    for c,t in zip(header[1:],techs):c.markdown(f'**{t}**')
    for ix,row in enumerate(rows):
        cols=st.columns(widths,vertical_alignment='center',gap='small')
        isusd='(USD/' in row
        label=row.replace('USD/stove','UGX/stove').replace('USD/firm','UGX/firm')
        cols[0].markdown(label)
        for c,t in zip(cols[1:],techs):
            raw=float(tab.at[row,t]); val=raw*fx if isusd else raw
            percent='(%)' in row
            upper=94.0 if row=='Profit margin (%)' else 100.0 if percent else max(10.,val*3.,1000. if 'sales' in row.lower() or 'cost' in row.lower() else 100.)
            step=.5 if percent else max(100.,round(max(val,1000)/200/100)*100) if isusd else 1.0
            new=c.slider(f'{row} – {t}',min_value=0.,max_value=float(upper),value=float(min(upper,val)),step=float(step),
                        label_visibility='collapsed',key=f'{st.session_state.reset_no}-{key}-{ix}-{t}-{fx if isusd else 0}',
                        help=f'{t}: {label}')
            c.caption(f'{new:,.0f}' if not percent else f'{new:,.1f}%')
            tab.at[row,t]=new/fx if isusd else new
    st.session_state.tables[key]=tab

with st.expander('How this model works',expanded=True):
    st.markdown('''The Excel workbook **260826_Economic_Incentives_Final model_V2.xlsm** separates the clean cooking market into **Early stage** and **Mid-stage**. Its calculation flow is **unit costs → company costs and annual stove sales → wages and profit → PAYE and CIT**. The workbook also has tax, assumptions, and industry sheets.

This simplified app keeps the same five clean cooking technologies as columns: **Ethanol, LPG, Electricity, Biogas and Biomass**. It applies the number of firms and years for each stage to the company figures. **No extra sales or workers are assumed because of incentives.**

For a transparent view of incentive costs, the charts show **CIT + PAYE minus illustrative tax relief**. This is a fiscal contribution indicator, **not a forecast of additional tax revenue compared with a no-incentive economy**. PAYE and CIT receipts are also shown separately.''')

st.info('**Demonstration recovery scenario:** Mid-stage defaults have higher annual stove sales and more workers, while the profit margin remains **40%**. Mid-stage VAT is set to **9%** (versus **0%** early and **18%** baseline) to illustrate partial withdrawal of incentives. These are demonstration assumptions, not measured impacts or prescribed tax rates. All remain editable.')

st.header('1. Number of firms and years')
st.caption('Each technology can have its own number of firms and duration of each stage.')
input_table('industry',INDUSTRY_NAMES)

st.header('2. Tax rates')
st.caption('Baseline = tax rates before the incentives. Change the early and mid-stage rates to test a policy.')
for tab,key in zip(st.tabs(['Baseline','Early stage','Mid-stage']),['tax_baseline','tax_early','tax_mid']):
    with tab:input_table(key,TAX_NAMES)

st.header('3. Company dynamics')
st.caption('DRIVING variables: editable sliders. DRIVEN variables: calculated automatically and read-only.')
for tab,key,tax_key in zip(st.tabs(['Early stage','Mid-stage']),['company_early','company_mid'],['tax_early','tax_mid']):
    with tab:
        st.markdown('**Driving variables — change these values**')
        input_table(key,COMPANY_NAMES)
        st.markdown('**Driven variables — calculated automatically (cannot be edited)**')
        import pandas as pd
        output_rows = {
            'Selling price per stove (UGX)': 'Selling price per stove (UGX)',
            'Total annual wages (UGX/firm)': 'Annual wages (UGX)',
            'Annual sales revenue (UGX/firm)': 'Annual sales revenue (UGX)',
            'Profit before CIT (UGX/firm)': 'Profit before CIT (UGX)',
            'PAYE (UGX/firm)': 'PAYE (UGX)',
            'CIT (UGX/firm)': 'CIT (UGX)',
        }
        techs_to_show = [technology] if phone else list(TECHS)
        out = {}
        for tech in techs_to_show:
            vals = calculate_company(st.session_state.tables[key][tech], st.session_state.tables[tax_key][tech],
                                     st.session_state.tables['tax_baseline'][tech], 1, settings)
            out[tech] = {label: vals[source] for label,source in output_rows.items()}
        st.dataframe(pd.DataFrame(out).style.format('{:,.0f}'), use_container_width=True)
        st.caption('Per firm, per year; results recalculate when the sliders above or the left-hand settings change. Selling price follows costs and the 40% target margin unless you edit that margin.')

try: annual,details=simulate(st.session_state.tables,settings)
except (ValueError,OverflowError) as e:st.error(str(e));st.stop()
if annual.empty:st.info('Set at least one stage to one year to see results.');st.stop()

st.header('4. Government revenue')
st.caption('Tax receipts from company income tax (CIT) and employee income tax (PAYE), plus a separate measure of tax relief.')
total_cit=annual['CIT (UGX)'].sum();total_paye=annual['PAYE (UGX)'].sum();relief=annual['Tax relief (UGX)'].sum()
a,b,c=st.columns(3)
a.metric('CIT collected',f'UGX {total_cit:,.0f}')
b.metric('PAYE collected',f'UGX {total_paye:,.0f}')
c.metric('Tax relief',f'UGX {relief:,.0f}')

fig=go.Figure()
fig.add_trace(go.Scatter(x=[settings.start_year-1]+annual['Year'].tolist(),y=[0]+annual['Cumulative fiscal contribution (UGX)'].tolist(),mode='lines+markers',name='CIT + PAYE − tax relief',line=dict(width=3,color='#087a86')))
fig.add_hline(y=0,line_dash='dash',line_color='#777')
# Highlight the first recovery year after the cumulative balance has been negative.
recovered = annual[(annual['Cumulative fiscal contribution (UGX)']>=0) &
                   (annual['Cumulative fiscal contribution (UGX)'].shift(1)<0)]
if not recovered.empty:
    recovery_year = int(recovered.iloc[0]['Year'])
    recovery_value = float(recovered.iloc[0]['Cumulative fiscal contribution (UGX)'])
    fig.add_trace(go.Scatter(x=[recovery_year],y=[recovery_value],mode='markers+text',
                             text=[f'Fiscal recovery: {recovery_year}'],textposition='top left',
                             marker=dict(size=12,color='#14803c'),name='Recovery year'))
fig.update_layout(height=450,margin=dict(l=10,r=10,t=30,b=10),xaxis_title='Year',yaxis_title='Cumulative fiscal contribution (UGX)')
st.plotly_chart(fig,use_container_width=True)
st.caption('Demonstration: the negative fiscal contribution can turn positive in the mid-stage as sales and employment grow and incentives are partly withdrawn. This is not proof that the incentives caused that growth or that the policy pays for itself.')

st.subheader('Revenue by technology')
view=st.radio('Choose result',['CIT + PAYE','CIT','PAYE','Tax relief','Cumulative fiscal contribution'],horizontal=True)
columns={'CIT + PAYE':'CIT + PAYE (UGX)','CIT':'CIT (UGX)','PAYE':'PAYE (UGX)','Tax relief':'Tax relief (UGX)','Cumulative fiscal contribution':'Fiscal contribution after relief (UGX)'}
chart=details[['Year','Technology',columns[view]]].copy()
if view=='Cumulative fiscal contribution':chart[columns[view]]=chart.groupby('Technology')[columns[view]].cumsum()
fig2=px.line(chart,x='Year',y=columns[view],color='Technology',markers=True,category_orders={'Technology':list(TECHS)})
fig2.update_layout(height=410,margin=dict(l=10,r=10,t=20,b=10))
st.plotly_chart(fig2,use_container_width=True)
summary=details.groupby(['Technology','Stage'],as_index=False)[['CIT (UGX)','PAYE (UGX)','Tax relief (UGX)','Fiscal contribution after relief (UGX)']].sum()
st.dataframe(summary.style.format({c:'{:,.0f}' for c in summary.columns if c.endswith('(UGX)')}),hide_index=True,use_container_width=True)

st.subheader('Download data')
a,b,c=st.columns(3)
a.download_button('Annual totals CSV',annual.to_csv(index=False).encode('utf-8-sig'),'annual_tax_results_ugx.csv',mime='text/csv',use_container_width=True)
b.download_button('Technology results CSV',details.to_csv(index=False).encode('utf-8-sig'),'technology_tax_results_ugx.csv',mime='text/csv',use_container_width=True)
scenario={'settings':settings.__dict__,'tables':{key:tab.to_dict() for key,tab in st.session_state.tables.items()}}
c.download_button('Save inputs JSON',json.dumps(scenario,indent=2).encode(),'clean_cooking_inputs.json',mime='application/json',use_container_width=True)
st.info('**Model limitations:** Imported costs and several company values are starting assumptions adapted from Excel; other costs and rates are illustrative. VAT relief uses a simplified gross sales basis. PAYE is a single effective rate. CIT omits depreciation, tax losses and other statutory adjustments. Withholding tax is not added to PAYE or CIT. Confirm the actual tax law and reconcile the workbook before using these outputs as official fiscal estimates.')
