"""Simplified illustrative fiscal model for conference discussion.

Uses direct business assumptions, never estimates extra sales or workers caused by incentives.
Tax relief is shown separately from CIT and PAYE. Not an audited replica of the XLSM.
"""
from dataclasses import dataclass
import pandas as pd

TECHS = ('Ethanol', 'LPG', 'Electricity', 'Biogas', 'Biomass')
TAX_NAMES = ('Import duty (%)', 'VAT (%)', 'Infrastructure levy (%)', 'Withholding tax (%)')
COMPANY_NAMES = ('Imported stove / parts cost (USD/stove)', 'Shipping and distribution (USD/stove)',
                 'Other expenses (USD/stove)', 'Annual fixed costs (USD/firm)',
                 'Annual stove sales (stoves/firm)', 'Direct workers (per firm)',
                 'Other workers (per firm)', 'Profit margin (%)')
INDUSTRY_NAMES = ('Number of firms - early stage', 'Number of firms - mid-stage',
                  'Early stage (years)', 'Mid-stage (years)')


def frame(rows):
    return pd.DataFrame(rows, index=TECHS).T.astype(float)


def defaults():
    baseline = {TAX_NAMES[0]:[10]*5,TAX_NAMES[1]:[18]*5,
                TAX_NAMES[2]:[1.5]*5,TAX_NAMES[3]:[6]*5}
    early = {k:v.copy() for k,v in baseline.items()}
    for k in TAX_NAMES[1:]: early[k]=[0]*5
    mid = {k:v.copy() for k,v in early.items()}
    early_co = {
        COMPANY_NAMES[0]:[20,40,45,2035,10],
        COMPANY_NAMES[1]:[2,3,4,75,1],
        COMPANY_NAMES[2]:[2,3,4,100,1],
        COMPANY_NAMES[3]:[100000,50000,50000,200000,100000],
        COMPANY_NAMES[4]:[10000,10000,10000,1000,50000],
        COMPANY_NAMES[5]:[0]*5,
        COMPANY_NAMES[6]:[30]*5,
        COMPANY_NAMES[7]:[40]*5,
    }
    mid_co = {k:v.copy() for k,v in early_co.items()}
    mid_co[COMPANY_NAMES[3]]=[200000,100000,500000,1000000,100000]
    mid_co[COMPANY_NAMES[4]]=[12000,30000,15000,800,40000]
    mid_co[COMPANY_NAMES[5]]=[40,200,100,40,800]
    mid_co[COMPANY_NAMES[6]]=[10,50,25,10,200]
    industry={INDUSTRY_NAMES[0]:[10,10,3,5,20], INDUSTRY_NAMES[1]:[10,10,3,5,20],
              INDUSTRY_NAMES[2]:[7]*5,INDUSTRY_NAMES[3]:[3]*5}
    return dict(tax_baseline=frame(baseline),tax_early=frame(early),tax_mid=frame(mid),
                company_early=frame(early_co),company_mid=frame(mid_co),industry=frame(industry))


@dataclass(frozen=True)
class Settings:
    fx:float=3505.0
    wage_ugx:float=3120000.0
    paye_pct:float=25.0
    cit_pct:float=30.0
    start_year:int=2027


def validate(tables, settings):
    if settings.fx<=0 or settings.wage_ugx<0 or not 0<=settings.paye_pct<=100 or not 0<=settings.cit_pct<=100:
        raise ValueError('Check exchange rate, wages, CIT and PAYE inputs.')
    for k,tab in tables.items():
        if list(tab.columns)!=list(TECHS) or not tab.notna().all().all() or (tab<0).any().any():
            raise ValueError(f'Invalid table: {k}')
        for row in tab.index:
            if '(%)' in row and (tab.loc[row]>100).any():
                raise ValueError(f'{row} cannot exceed 100%.')
    for phase in ('company_early','company_mid'):
        if (tables[phase].loc[COMPANY_NAMES[7]]>=95).any():
            raise ValueError('Profit margin must be below 95%.')
    if (tables['industry'].loc[list(INDUSTRY_NAMES[2:])]>40).any().any():
        raise ValueError('Stage duration cannot exceed 40 years.')


def calculate_company(co, tax, baseline_tax, firms, settings):
    """One annual technology calculation, UGX throughout.

    VAT relief is a simple gross proxy on pre-VAT sales; withholdings are displayed
    but excluded from fiscal contribution to avoid assuming they're additional tax.
    """
    fx=settings.fx
    units=float(co[COMPANY_NAMES[4]])*firms
    cif=units*float(co[COMPANY_NAMES[0]])*fx
    shipping=units*float(co[COMPANY_NAMES[1]])*fx
    other=units*float(co[COMPANY_NAMES[2]])*fx
    fixed=firms*float(co[COMPANY_NAMES[3]])*fx
    workers=firms*(float(co[COMPANY_NAMES[5]])+float(co[COMPANY_NAMES[6]]))
    wages=workers*settings.wage_ugx
    duty=cif*float(tax[TAX_NAMES[0]])/100
    levy=cif*float(tax[TAX_NAMES[2]])/100
    total_cost=cif+shipping+other+fixed+wages+duty+levy
    margin=float(co[COMPANY_NAMES[7]])/100
    sales=total_cost/(1-margin) if units else 0
    profit=max(sales-total_cost,0)
    cit=profit*settings.cit_pct/100
    paye=wages*settings.paye_pct/100
    vat=sales*float(tax[TAX_NAMES[1]])/100
    tax_relief=max(0,cif*(float(baseline_tax[TAX_NAMES[0]])-float(tax[TAX_NAMES[0]]))/100)
    tax_relief+=max(0,cif*(float(baseline_tax[TAX_NAMES[2]])-float(tax[TAX_NAMES[2]]))/100)
    tax_relief+=max(0,sales*(float(baseline_tax[TAX_NAMES[1]])-float(tax[TAX_NAMES[1]]))/100)
    withholding=cif*float(tax[TAX_NAMES[3]])/100
    return {
        'Annual stove sales':units,'Workers':workers,'Total company costs (UGX)':total_cost,
        'Selling price per stove (UGX)':sales/units if units else 0,
        'Profit before CIT (UGX)':profit,'CIT (UGX)':cit,'PAYE (UGX)':paye,
        'Import duty (UGX)':duty,'Infrastructure levy (UGX)':levy,'VAT (UGX)':vat,
        'Withholding tax (UGX; shown only)':withholding,
        'Tax relief (UGX)':tax_relief,
        'CIT + PAYE (UGX)':cit+paye,
        'Fiscal contribution after relief (UGX)':cit+paye-tax_relief,
    }


def simulate(tables, settings):
    validate(tables,settings)
    records=[]
    industry=tables['industry']
    years_max=int((industry.loc[INDUSTRY_NAMES[2]]+industry.loc[INDUSTRY_NAMES[3]]).max())
    for yr in range(years_max):
        for tech in TECHS:
            early=int(industry.at[INDUSTRY_NAMES[2],tech]);mid=int(industry.at[INDUSTRY_NAMES[3],tech])
            if yr>=early+mid:continue
            phase='Early stage' if yr<early else 'Mid-stage'
            is_early=yr<early
            firms=float(industry.at[INDUSTRY_NAMES[0] if is_early else INDUSTRY_NAMES[1],tech])
            co=tables['company_early' if is_early else 'company_mid'][tech]
            tax=tables['tax_early' if is_early else 'tax_mid'][tech]
            result=calculate_company(co,tax,tables['tax_baseline'][tech],firms,settings)
            records.append({'Year':settings.start_year+yr,'Technology':tech,'Stage':phase,
                            'Number of firms':firms,**result})
    details=pd.DataFrame(records)
    if details.empty:return pd.DataFrame(),details
    annual=details.groupby('Year',as_index=False)[['CIT (UGX)','PAYE (UGX)','CIT + PAYE (UGX)',
             'Tax relief (UGX)','Fiscal contribution after relief (UGX)']].sum()
    annual['Cumulative fiscal contribution (UGX)']=annual['Fiscal contribution after relief (UGX)'].cumsum()
    return annual,details
