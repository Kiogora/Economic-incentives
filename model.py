"""Transparent illustrative clean-cooking fiscal model. All financial computations use UGX.

Workbook source: 260826_Economic_Incentives_Final model_V2.xlsm.
This is a model adaptation, not a validated replication of workbook formulas.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
import pandas as pd

TECHS = ('Ethanol', 'LPG', 'Electricity', 'Biogas', 'Biomass')
TAX_NAMES = (
    'Import duty - finished stove (%)', 'VAT - finished stove (%)',
    'Infrastructure levy - stove (%)', 'Withholding tax - stove (%)',
    'Import duty - parts (%)', 'Infrastructure levy - parts (%)',
    'VAT - locally made stove (%)',
)
COMPANY_NAMES = (
    'Imported stove cost (USD/unit)', 'Shipping and distribution (USD/unit)',
    'Other expenses (USD/unit)', 'Annual fixed costs (USD/firm)',
    'Annual stove sales (units/firm)', 'Direct workers (per firm)',
    'Other workers (per firm)', 'Profit margin (%)',
    'Stoves made in Uganda (%)', 'Local content (%)',
    'Extra local sourcing cost (%)', 'Annual stove demand (units)',
    'Extra sales with incentives (%)', 'Sales without incentives (units/firm)',
    'Firms without incentives (%)', 'Workers without incentives (%)',
)
INDUSTRY_NAMES = ('Firms - early stage', 'Firms - mid-stage', 'Early stage (years)',
                  'Mid-stage (years)', 'Annual stove sales growth (%)')


def frame(spec):
    return pd.DataFrame(spec, index=TECHS).T.astype(float)


def defaults():
    baseline = {
        TAX_NAMES[0]:[10]*5, TAX_NAMES[1]:[18]*5,
        TAX_NAMES[2]:[1.5]*5, TAX_NAMES[3]:[6]*5,
        TAX_NAMES[4]:[10]*5, TAX_NAMES[5]:[1.5]*5,
        TAX_NAMES[6]:[18]*5,
    }
    early = {k:v.copy() for k,v in baseline.items()}
    for k in [TAX_NAMES[1],TAX_NAMES[2],TAX_NAMES[3],TAX_NAMES[5],TAX_NAMES[6]]:
        early[k] = [0]*5
    mid = {k:v.copy() for k,v in early.items()}
    mid[TAX_NAMES[4]] = [0]*5
    data = {
       COMPANY_NAMES[0]: [20,40,45,2035,10], # workbook early stage - unit effects row 69
       COMPANY_NAMES[1]: [2,3,4,75,1], # scenario assumptions, not audited workbook values
       COMPANY_NAMES[2]: [2,3,4,100,1],
       COMPANY_NAMES[3]: [100000,50000,50000,200000,100000], # early firm effects row 9
       COMPANY_NAMES[4]: [10000,10000,10000,1000,50000], # early firm effects row 10
       COMPANY_NAMES[5]: [0]*5, COMPANY_NAMES[6]: [30]*5,
       COMPANY_NAMES[7]: [40]*5, COMPANY_NAMES[8]: [0]*5,
       COMPANY_NAMES[9]: [0]*5, COMPANY_NAMES[10]: [0]*5,
       COMPANY_NAMES[11]: [100000,200000,100000,10000,500000],
       COMPANY_NAMES[12]: [0]*5,
       COMPANY_NAMES[13]: [20000,20000,20000,2000,100000], # early firm effects row 11
       COMPANY_NAMES[14]: [100]*5, COMPANY_NAMES[15]: [100]*5,
    }
    midco = {k:v.copy() for k,v in data.items()}
    midco[COMPANY_NAMES[3]] = [200000,100000,500000,1000000,100000]
    midco[COMPANY_NAMES[4]] = [12000,30000,15000,800,40000] # demo firm sales, NOT workbook output
    midco[COMPANY_NAMES[5]] = [40,200,100,40,800]
    midco[COMPANY_NAMES[6]] = [10,50,25,10,200]
    midco[COMPANY_NAMES[8]] = [90]*5
    midco[COMPANY_NAMES[9]] = [15,10,10,10,10]
    midco[COMPANY_NAMES[10]] = [35]*5
    midco[COMPANY_NAMES[11]] = [120000,300000,150000,40000,800000]
    midco[COMPANY_NAMES[12]] = [20]*5
    midco[COMPANY_NAMES[13]] = [10000,10000,5000,600,20000]
    midco[COMPANY_NAMES[14]] = [80]*5
    midco[COMPANY_NAMES[15]] = [60]*5
    industry = {
       INDUSTRY_NAMES[0]: [10,10,3,5,20], INDUSTRY_NAMES[1]: [10,10,3,5,20],
       INDUSTRY_NAMES[2]: [7]*5, INDUSTRY_NAMES[3]: [3]*5,
       INDUSTRY_NAMES[4]: [0]*5, # growth not directly specified in workbook
    }
    return {'tax_baseline':frame(baseline),'tax_early':frame(early),
            'tax_mid':frame(mid),'company_early':frame(data),
            'company_mid':frame(midco),'industry':frame(industry)}


@dataclass(frozen=True)
class Settings:
    fx: float = 3505.0
    wage_ugx: float = 260000*12
    paye_pct: float = 25
    cit_pct: float = 30
    start_year: int = 2027


def validate(models:Mapping[str,pd.DataFrame], config:Settings):
    assert config.fx > 0 and config.wage_ugx >= 0
    assert 0 <= config.paye_pct <= 100 and 0 <= config.cit_pct <= 100
    for name, tab in models.items():
        assert list(tab.columns)==list(TECHS),name
        assert tab.notna().all().all() and (tab>=0).all().all(), f'Negative/blank entry in {name}'
        assert tab.map(lambda x: x==x and x!=float('inf')).all().all()
        for row in tab.index:
            if '(%)' in row:
                assert (tab.loc[row] <= 100).all(),f'Percentage over 100: {row}'
    for phase in ['company_early','company_mid']:
        assert (models[phase].loc[COMPANY_NAMES[7]]<95).all(), 'Profit margin must be below 95%'
    years=models['industry'].loc[[INDUSTRY_NAMES[2],INDUSTRY_NAMES[3]]]
    assert (years <= 60).all().all(), 'Phase duration cannot exceed 60 years'


def company_fiscal(co:pd.Series, tax:pd.Series, *, units:float, firms:float,
                   config:Settings, with_policy:bool, worker_multiplier:float=1.0):
    """Returns fiscal amounts for one technology/year in UGX.

    Important: VAT is an illustrative gross tax proxy, not verified net VAT after input credits.
    Withholding is informational, not additional net tax, to avoid credit double counting.
    """
    q=max(0.,units); n=max(0.,firms)
    fx=config.fx
    cif=co[COMPANY_NAMES[0]]*fx
    imported_share=1-co[COMPANY_NAMES[8]]/100 if with_policy else 1.0
    local_share=1-imported_share
    content=(co[COMPANY_NAMES[9]]/100) if with_policy else 0.0
    extra=(co[COMPANY_NAMES[10]]/100) if with_policy else 0.0
    finished_import_value=q*imported_share*cif
    parts_import_value=q*local_share*cif*(1-content)
    local_input_cost=q*local_share*cif*(1+content*extra)
    duty=finished_import_value*tax[TAX_NAMES[0]]/100+parts_import_value*tax[TAX_NAMES[4]]/100
    levy=finished_import_value*tax[TAX_NAMES[2]]/100+parts_import_value*tax[TAX_NAMES[5]]/100
    workers=n*(co[COMPANY_NAMES[5]]+co[COMPANY_NAMES[6]])*worker_multiplier
    wages=workers*config.wage_ugx
    fixed=n*co[COMPANY_NAMES[3]]*fx
    expenses=q*(co[COMPANY_NAMES[1]]+co[COMPANY_NAMES[2]])*fx
    cost=finished_import_value+local_input_cost+duty+levy+fixed+expenses+wages
    margin=co[COMPANY_NAMES[7]]/100
    sales=cost/(1-margin) if q>0 else 0.
    profit=max(0.,sales-cost)
    # A simplified VAT receipt proxy on taxable appliance sales. Real-world import input VAT
    # recoverability, VAT inclusive/exclusive pricing and credits must be analysed separately.
    vat=sales*(imported_share*tax[TAX_NAMES[1]]+local_share*tax[TAX_NAMES[6]])/100
    withholding=finished_import_value*tax[TAX_NAMES[3]]/100
    ret={
        'Import duty':duty,'Infrastructure levy':levy,'VAT (simplified)':vat,
        'PAYE':wages*config.paye_pct/100,'CIT':profit*config.cit_pct/100,
        'Withholding (gross only)':withholding,
        'Total company costs':cost,'Annual company sales':sales,
        'Company profit before CIT':profit,'Annual stove sales':q,
        'Workers':workers,'Selling price per stove':sales/q if q else 0.,
        'Cost per stove':cost/q if q else 0.,
    }
    return ret


def simulate(models:Mapping[str,pd.DataFrame], config:Settings):
    validate(models,config)
    industry=models['industry']
    max_year=min(100,int((industry.loc[INDUSTRY_NAMES[2]]+industry.loc[INDUSTRY_NAMES[3]]).max()))
    records=[]
    keys=('Import duty','Infrastructure levy','VAT (simplified)','PAYE','CIT')
    for i in range(max_year):
        for tech in TECHS:
            early=int(industry.loc[INDUSTRY_NAMES[2],tech]);mid=int(industry.loc[INDUSTRY_NAMES[3],tech])
            if i>=early+mid:continue
            isearly=i<early
            stage='Early stage' if isearly else 'Mid-stage'
            co=models['company_early' if isearly else 'company_mid'][tech]
            tax=models['tax_early' if isearly else 'tax_mid'][tech]
            baseline_tax=models['tax_baseline'][tech]
            firms=industry.loc[INDUSTRY_NAMES[0] if isearly else INDUSTRY_NAMES[1],tech]
            growth=(1+industry.loc[INDUSTRY_NAMES[4],tech]/100)**i
            nbase=firms*co[COMPANY_NAMES[14]]/100
            ceiling=co[COMPANY_NAMES[11]]
            base_units=min(ceiling,nbase*co[COMPANY_NAMES[13]]*growth)
            pol_units=min(ceiling,firms*co[COMPANY_NAMES[4]]*growth*(1+co[COMPANY_NAMES[12]]/100))
            pol=company_fiscal(co,tax,units=pol_units,firms=firms,config=config,with_policy=True)
            bas=company_fiscal(co,baseline_tax,units=base_units,firms=nbase,config=config,
                               with_policy=False,worker_multiplier=co[COMPANY_NAMES[15]]/100)
            out={'Year':config.start_year+i,'Technology':tech,'Stage':stage,
                 'Annual stove sales':pol_units,'Stove sales without incentives':base_units,
                 'Selling price per stove (UGX)':pol['Selling price per stove'],
                 'Total company costs (UGX)':pol['Total company costs'],
                 'Company profit before CIT (UGX)':pol['Company profit before CIT'],
                 'Workers':pol['Workers']}
            for k in keys:
                out['With incentives - '+k]=pol[k]
                out['Without incentives - '+k]=bas[k]
                out['Change - '+k]=pol[k]-bas[k]
            out['Withholding (gross only)']=pol['Withholding (gross only)']
            out['Government revenue with incentives (UGX)']=sum(pol[k] for k in keys)
            out['Government revenue without incentives (UGX)']=sum(bas[k] for k in keys)
            out['Change in government revenue (UGX)']=out['Government revenue with incentives (UGX)']-out['Government revenue without incentives (UGX)']
            records.append(out)
    if not records:
        return pd.DataFrame(),pd.DataFrame()
    detail=pd.DataFrame(records)
    annual=detail.groupby('Year',as_index=False)[['Government revenue with incentives (UGX)',
       'Government revenue without incentives (UGX)','Change in government revenue (UGX)']].sum()
    annual['Cumulative change (UGX)']=annual['Change in government revenue (UGX)'].cumsum()
    return annual,detail
