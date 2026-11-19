"""Interactive Uganda clean cooking fiscal simulator.
Defaults are seeded from 260826_Economic_Incentives_Final model_V2.xlsm,
NOT a complete or audited reconstruction of the spreadsheet's formulas.
Tax bases, demand response and counterfactuals are simplified; validate for policy use.
"""
from __future__ import annotations
import io, json, zipfile
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title='Uganda Clean Cooking | Fiscal Simulator', page_icon='🔥', layout='wide')
TECHS=['Ethanol','LPG','Electricity','Biogas','Biomass']
STAGES=['Early stage','Mid-stage']
CIF=[20,40,45,2035,10]
EARLY_FIXED=[100000,50000,50000,200000,100000]
EARLY_UNITS=[3000,3000,3000,300,15000]
MID_FIXED=[200000,100000,500000,1000000,100000]
MID_CAP=[100000,1000000,500000,5000,700000]
MID_WORKERS=[50,250,125,50,1000]
MID_DEMAND=[120000,300000,150000,40000,800000]
EARLY_FIRMS=[10,10,3,5,20]
MID_FIRMS=[10,10,3,5,20]

def matrix(rows:dict)->pd.DataFrame:
    return pd.DataFrame(rows,index=TECHS).T.astype(float)

def init():
    # All monetary values in USD; percentage entries expressed 0-100.
    base_tax={
      'Imported stove duty (%)':[10]*5, 'Imported stove VAT (%)':[18]*5,
      'Imported stove infrastructure levy (%)':[1.5]*5,
      'Imported stove withholding (%)':[6]*5,
      'CKD/components duty (%)':[10]*5, 'CKD/components levy (%)':[1.5]*5,
      'Locally made stove VAT (%)':[0,18,18,18,18]
    }
    early_tax={k:list(v) for k,v in base_tax.items()}
    # Early stage incentive schedule: use the user workbook's imported-stove rates
    # but allow override. Local VAT relief represented by zero-rated assumption.
    early_tax['Locally made stove VAT (%)']=[0]*5
    mid_tax={k:list(v) for k,v in early_tax.items()}
    mid_tax['Imported stove VAT (%)']=[0]*5
    mid_tax['Imported stove infrastructure levy (%)']=[0]*5
    mid_tax['Imported stove withholding (%)']=[0]*5
    mid_tax['CKD/components duty (%)']=[0]*5
    mid_tax['CKD/components levy (%)']=[0]*5
    baseline={
        'Stove CIF imported cost (USD/unit)':CIF,
        'Distribution / shipping (USD/unit)':[2,3,4,75,1],
        'Other variable expense (USD/unit)':[2,3,4,100,1],
        'Fixed operating expenses (USD/firm/year)':EARLY_FIXED,
        'Units sold / firm / year':EARLY_UNITS,
        'Direct workers / firm':[0]*5,
        'Indirect workers / firm':[30]*5,
        'Annual salary / worker (USD)':[890.1569]*5,
        'Target pre-CIT profit margin (%)':[40]*5,
        'Locally made share of appliance units (%)':[0]*5,
        'Local content share of input value (%)':[0]*5,
        'Local sourcing cost premium (%)':[0]*5,
        'Annual demand ceiling (units/vertical)':[100000,200000,100000,10000,500000],
        'Policy sales uplift over baseline (%)':[0]*5,
        'Baseline annual units / firm':EARLY_UNITS,
        'Baseline firms relative to policy (%)':[100]*5,
        'Baseline employment relative to policy (%)':[100]*5,
    }
    mid={
        'Stove CIF imported cost (USD/unit)':CIF,
        'Distribution / shipping (USD/unit)':[2,3,4,75,1],
        'Other variable expense (USD/unit)':[2,3,4,100,1],
        'Fixed operating expenses (USD/firm/year)':MID_FIXED,
        'Units sold / firm / year':[12000,30000,15000,800,40000],
        'Direct workers / firm':[40,200,100,40,800],
        'Indirect workers / firm':[10,50,25,10,200],
        'Annual salary / worker (USD)':[890.1569]*5,
        'Target pre-CIT profit margin (%)':[40]*5,
        'Locally made share of appliance units (%)':[90]*5,
        'Local content share of input value (%)':[15,10,10,10,10],
        'Local sourcing cost premium (%)':[35]*5,
        'Annual demand ceiling (units/vertical)':MID_DEMAND,
        'Policy sales uplift over baseline (%)':[20]*5,
        'Baseline annual units / firm':[10000,10000,5000,600,20000],
        'Baseline firms relative to policy (%)':[80]*5,
        'Baseline employment relative to policy (%)':[60]*5,
    }
    industry={
       'Early-stage firms':EARLY_FIRMS,'Mid-stage firms':MID_FIRMS,
       'Early-stage duration (years)':[7]*5,'Mid-stage duration (years)':[3]*5,
       'Annual unit sales growth (%)':[20]*5
    }
    st.session_state.models={
      'baseline_tax':matrix(base_tax),'early_tax':matrix(early_tax),'mid_tax':matrix(mid_tax),
      'early_company':matrix(baseline),'mid_company':matrix(mid),'industry':matrix(industry)
    }
    st.session_state.editor_rev=0
    st.session_state.slider_row='Stove CIF imported cost (USD/unit)'
    st.session_state.slider_stage='Early stage'

if 'models' not in st.session_state:init()

PERCENT_HINT='Rates are entered as percentages (e.g., 18 means 18%).'
st.title('Uganda Clean Cooking — Fiscal Incentives Simulator')
st.caption('Editable columns: ethanol, LPG, electricity, biogas and biomass. Workbook-seeded inputs; simplified and independently recalculated fiscal model.')
st.info('**Important:** This prototype uses selected inputs from the uploaded V2 workbook. It is not a cell-for-cell Excel replica. VAT is modelled as a simplified net transaction tax; withholding is excluded from net revenue because it may be creditable against income tax. Validate legal tax bases and counterfactual assumptions before relying on the outputs.')

with st.sidebar:
 st.header('Simulation settings')
 start_year=st.number_input('First simulation year',min_value=2020,max_value=2100,value=2027,step=1)
 paye=st.slider('Effective PAYE rate (%)',0.0,50.0,25.0,1.0)
 cit=st.slider('Corporate income tax rate (%)',0.0,50.0,30.0,1.0)
 st.caption('PAYE and CIT are simplified effective rates, not statutory tax calculations.')
 include_wht=st.checkbox('Show withholding in gross cash collections (not net fiscal impact)',value=False)
 if st.button('Restore workbook-seeded assumptions',use_container_width=True):
  init();st.rerun()

st.subheader('1. Industry structure')
st.caption('Each vertical can have its own firm counts and duration of incentives. After the early period, that vertical enters the mid-stage; all verticals share a common calendar.')

def edit_matrix(name,title):
 st.markdown('**'+title+'**')
 df=st.session_state.models[name]
 out=st.data_editor(df,use_container_width=True,num_rows='fixed',key=f'edit_{name}_{st.session_state.editor_rev}',
                    column_config={t:st.column_config.NumberColumn(t,min_value=0.0,step=1.0,format='%.2f') for t in TECHS})
 st.session_state.models[name]=out.astype(float)
 return out

industry=edit_matrix('industry','Firm counts, incentive durations and annual growth')

st.subheader('2. Tax tables')
st.caption(PERCENT_HINT+' Baseline means no new incentive; early and mid tables are the corresponding policy scenarios.')
for name,label in [('baseline_tax','No-incentive baseline'),('early_tax','Early-stage incentive rates'),('mid_tax','Mid-stage incentive rates')]:
 with st.expander(label,expanded=name=='early_tax'):
  edit_matrix(name,label)

st.subheader('3. Company dynamics')
tabs=st.tabs(STAGES)
for tab,stage,name in zip(tabs,STAGES,['early_company','mid_company']):
 with tab:
  edit_matrix(name,stage+' — cost, staffing, volume and margin assumptions')
  st.caption('Fixed costs and salaries enter total cost; the target pre-CIT margin determines the modelled selling price. Imported CIF cost drives import duty and import levies. Local content and its cost premium determine the local input cost.')

st.subheader('4. Slider-based sensitivity')
st.caption('Choose a row and technology, then move the slider. The matching cell in the company assumption table updates, and all outputs recalculate.')
c1,c2,c3=st.columns([1,1,2])
with c1:sl_stage=st.selectbox('Stage',STAGES,key='slider_stage')
key='early_company' if sl_stage=='Early stage' else 'mid_company'
with c2:sl_tech=st.selectbox('Technology',TECHS)
with c3:sl_row=st.selectbox('Company assumption',list(st.session_state.models[key].index),key='slider_row')
old=float(st.session_state.models[key].loc[sl_row,sl_tech])
if '(%)' in sl_row:
 low,high,step=0.0,100.0,1.0
elif 'units' in sl_row.lower() or 'workers' in sl_row.lower():
 low,high,step=0.0,max(100.0,old*3,1.0),1.0
else:
 low,high,step=0.0,max(100.0,old*3,1.0),max(.01,round(max(old,1.0)/100,2))
new=st.slider(f'{sl_row} · {sl_tech}',min_value=low,max_value=float(high),value=min(old,float(high)),step=float(step))
if abs(new-old)>1e-8:
 st.session_state.models[key].loc[sl_row,sl_tech]=new
 st.session_state.editor_rev+=1
 st.rerun()

# All calculations are recomputed from the current table state, NOT from excel cached outputs.
def pct(v):return float(v)/100.0

def fiscal_unit(c,tx,units,firms,policy=True,baseline_firms_ratio=1.,baseline_staff_ratio=1.):
 """Return fiscal flows and per-unit cost breakdown for one technology-year."""
 u=max(0.,float(units));n=max(0.,float(firms))
 cif=c['Stove CIF imported cost (USD/unit)']
 local_share=pct(c['Locally made share of appliance units (%)']) if policy else 0.
 content=pct(c['Local content share of input value (%)']) if policy else 0.
 premium=pct(c['Local sourcing cost premium (%)']) if policy else 0.
 local_material=cif*((1-content)+content*(1+premium))
 # On local units, only imported material content is subject to duty/levy.
 imported_value=u*(1-local_share)*cif
 parts_value=u*local_share*cif*(1-content)
 duty=imported_value*pct(tx['Imported stove duty (%)'])+parts_value*pct(tx['CKD/components duty (%)'])
 levy=imported_value*pct(tx['Imported stove infrastructure levy (%)'])+parts_value*pct(tx['CKD/components levy (%)'])
 # Expenses and wages for the whole firm (fixed expenses are NOT counted as sales tax bases).
 wage=float(c['Annual salary / worker (USD)'])
 workers=(float(c['Direct workers / firm'])+float(c['Indirect workers / firm']))*(baseline_staff_ratio if not policy else 1.)*n
 annual_wages=workers*wage
 fixed=n*float(c['Fixed operating expenses (USD/firm/year)'])
 imported_material=u*(1-local_share)*cif
 local_material_total=u*local_share*local_material
 other_variable=u*(float(c['Distribution / shipping (USD/unit)'])+float(c['Other variable expense (USD/unit)']))
 total_cost=imported_material+local_material_total+duty+levy+other_variable+annual_wages+fixed
 margin=np.clip(pct(c['Target pre-CIT profit margin (%)']),0.,.95)
 # Baseline sales price based on same cost-plus-margin assumption; can later be calibrated separately.
 sales_revenue=total_cost/(1-margin) if u>0 else 0.
 pretax_profit=max(0.,sales_revenue-total_cost)
 # Simplified VAT: charge output VAT on ex-VAT sales; input VAT credit not estimated.
 vat_rate=pct(tx['Imported stove VAT (%)'])*(1-local_share)+pct(tx['Locally made stove VAT (%)'])*local_share
 vat=sales_revenue*vat_rate
 # Withholding is generally creditable: displayed as gross cash flow, excluded from fiscal delta.
 wht=imported_value*pct(tx['Imported stove withholding (%)'])
 return {'Import duty':duty,'Infrastructure levy':levy,'VAT (simplified)':vat,
   'PAYE':annual_wages*paye/100.,'CIT':pretax_profit*cit/100.,
   'Withholding (gross only)':wht,'Total company cost':total_cost,
   'Turnover ex-VAT':sales_revenue,'Operating profit pre-CIT':pretax_profit,
   'Appliances':u,'Workers':workers,'Unit selling price ex-VAT':sales_revenue/u if u>0 else 0.,
   'Unit company cost':total_cost/u if u>0 else 0.}

for name,df in st.session_state.models.items():
 if df.isna().any().any() or (df.values<0).any() or not np.isfinite(df.values).all():
  st.error(f'Invalid negative, blank or non-numeric value in {name}.');st.stop()
for phase in ['early_company','mid_company']:
 if (st.session_state.models[phase].loc['Target pre-CIT profit margin (%)']>=95).any():
  st.error('The target margin must be below 95% to avoid an unstable selling price.');st.stop()

models=st.session_state.models
max_year=int(np.max(industry.loc['Early-stage duration (years)']+industry.loc['Mid-stage duration (years)']))
max_year=min(max_year,80)
rows=[];detail=[]
for i in range(max_year):
 for tech in TECHS:
  early=int(industry.loc['Early-stage duration (years)',tech]);mid=int(industry.loc['Mid-stage duration (years)',tech]);
  if i>=early+mid:continue
  phase='Early stage' if i<early else 'Mid-stage'
  company=models['early_company' if phase=='Early stage' else 'mid_company'][tech]
  tax=models['early_tax' if phase=='Early stage' else 'mid_tax'][tech]
  base_tax=models['baseline_tax'][tech]
  firms=industry.loc['Early-stage firms' if phase=='Early stage' else 'Mid-stage firms',tech]
  annual_growth=(1+pct(industry.loc['Annual unit sales growth (%)',tech]))**i
  base_firms=firms*pct(company['Baseline firms relative to policy (%)'])
  demand=company['Annual demand ceiling (units/vertical)']
  base_u=min(demand,base_firms*company['Baseline annual units / firm']*annual_growth)
  policy_u=min(demand,firms*company['Units sold / firm / year']*annual_growth*(1+pct(company['Policy sales uplift over baseline (%)'])))
  pol=fiscal_unit(company,tax,policy_u,firms,True)
  bas=fiscal_unit(company,base_tax,base_u,base_firms,False,baseline_staff_ratio=pct(company['Baseline employment relative to policy (%)']))
  keys=['Import duty','Infrastructure levy','VAT (simplified)','PAYE','CIT']
  delta=sum(pol[k]-bas[k] for k in keys)
  result={'Year':int(start_year)+i,'Technology':tech,'Stage':phase,'Net fiscal impact (USD)':delta,
     'Policy sales (units)':policy_u,'Baseline sales (units)':base_u,
     'Policy selling price (USD/unit)':pol['Unit selling price ex-VAT'],
     'Policy total company cost (USD)':pol['Total company cost'],
     'Policy operating profit (USD)':pol['Operating profit pre-CIT']}
  for k in keys:
   result[f'Policy {k}']=pol[k];result[f'Baseline {k}']=bas[k];result[f'Delta {k}']=pol[k]-bas[k]
  if include_wht:result['Policy gross withholding (USD)']=pol['Withholding (gross only)']
  detail.append(result)
  rows.append({'Year':int(start_year)+i,'Technology':tech,'Stage':phase,'Delta':delta})

if not rows:
 st.warning('Enter at least one nonzero stage duration.');st.stop()
annual=pd.DataFrame(rows).groupby('Year',as_index=False)['Delta'].sum()
annual['Cumulative fiscal impact (USD)']=annual['Delta'].cumsum()
details=pd.DataFrame(detail)

st.subheader('5. Cumulative government revenue impact')
st.caption('Cumulative net incremental taxes relative to the no-incentive scenario; negative values represent net revenue forgone.')
plot=go.Figure()
plot.add_trace(go.Scatter(x=[start_year-1]+annual['Year'].tolist(),y=[0]+annual['Cumulative fiscal impact (USD)'].tolist(),mode='lines+markers',name='Cumulative fiscal impact',line=dict(width=3,color='#2277b8')))
plot.add_hline(y=0,line_dash='dash',line_color='#7c8792')
# Because technologies can have distinct durations, mark the end of the longest early stage.
cut=int(industry.loc['Early-stage duration (years)'].max())
if cut>0:plot.add_vline(x=start_year+cut-.5,line_dash='dash',line_color='#e0a349',annotation_text='Last vertical enters mid-stage',annotation_position='top right')
positive=annual[annual['Cumulative fiscal impact (USD)']>=0]
negative=annual[annual['Cumulative fiscal impact (USD)']<0]
if not positive.empty and not negative.empty:
 crossover=positive.iloc[0]
 plot.add_annotation(x=int(crossover['Year']),y=float(crossover['Cumulative fiscal impact (USD)']),text=f"Cumulative break-even: {int(crossover['Year'])}",showarrow=True,arrowhead=2,ay=-50)
plot.update_layout(height=480,margin=dict(l=15,r=15,t=35,b=20),xaxis_title='Calendar year',yaxis_title='Cumulative net revenue (USD)',hovermode='x unified')
st.plotly_chart(plot,use_container_width=True)
last=float(annual['Cumulative fiscal impact (USD)'].iloc[-1]);total_policy=details[[k for k in details if k.startswith('Policy ') and k[7:] in ['Import duty','Infrastructure levy','VAT (simplified)','PAYE','CIT']]].sum().sum()
a,b,c=st.columns(3)
a.metric('Cumulative fiscal impact',f'USD {last:,.0f}')
b.metric('Total policy tax receipts',f'USD {total_policy:,.0f}')
c.metric('Break-even year',str(int(positive.iloc[0]['Year'])) if not positive.empty and not negative.empty else 'Not reached')

st.subheader('6. Fiscal breakdown')
by_tax=details[[c for c in details if c.startswith('Delta ') and c!='Delta']].sum().rename(lambda x:x.replace('Delta ','')).reset_index()
by_tax.columns=['Tax category','Net change (USD)']
st.dataframe(by_tax,use_container_width=True,hide_index=True)
by_tech=details.groupby('Technology',as_index=False)['Net fiscal impact (USD)'].sum()
st.plotly_chart(go.Figure(go.Bar(x=by_tech['Technology'],y=by_tech['Net fiscal impact (USD)'],marker_color='#317b9f')).update_layout(height=350,yaxis_title='Cumulative incremental USD',margin=dict(t=15,b=15)),use_container_width=True)
with st.expander('Detailed annual tax and company calculations'):
 st.dataframe(details,use_container_width=True,hide_index=True)

st.subheader('7. Export and review assumptions')
cb1,cb2,cb3=st.columns(3)
with cb1:st.download_button('Download annual results (CSV)',annual.to_csv(index=False).encode(),file_name='fiscal_annual.csv',mime='text/csv',use_container_width=True)
with cb2:st.download_button('Download detail (CSV)',details.to_csv(index=False).encode(),file_name='fiscal_by_technology.csv',mime='text/csv',use_container_width=True)
with cb3:
 payload={k:v.to_dict(orient='index') for k,v in models.items()}
 st.download_button('Download scenario (JSON)',json.dumps({'tables':payload,'first_year':start_year,'paye_rate_pct':paye,'cit_rate_pct':cit},indent=2),file_name='fiscal_scenario.json',mime='application/json',use_container_width=True)
st.caption('Model limitations: output VAT is not netted against actual input VAT credits; early-stage and baseline prices use a cost-plus assumption; CIT omits losses, depreciation and tax shields; fuel taxes and fuel sales are excluded; no cross-year firm transitions or cohort tracking; sales demand and firm growth are user-controlled, not econometrically estimated. Withholding is shown separately as gross cash only.')
