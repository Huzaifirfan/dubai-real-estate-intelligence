"""Read-only Stage 11 validation; evidence is confined to this directory."""
import collections
import csv
import hashlib
import json
import re
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROJECT = ROOT / 'powerbi/Dubai_Real_Estate_Intelligence'
REPORT = PROJECT / 'Dubai_Real_Estate_Intelligence.Report'
MODEL = PROJECT / 'Dubai_Real_Estate_Intelligence.SemanticModel/definition'
SOURCE = ROOT / 'data/processed/dld_transactions_2026_ytd_features.csv'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(ROOT),*args],text=True)
def save(name,obj): (HERE/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def main():
    errors=[]
    def check(condition,message):
        if not condition: errors.append(message)
    baseline=read(HERE/'recovery_baseline.json')
    before=sha(SOURCE)
    with SOURCE.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);columns=reader.fieldnames;rows=list(reader)
    sales=[r for r in rows if r['GROUP_EN']=='Sales']
    prices=[float(r['SALE_PRICE_PER_SQFT']) for r in sales if r['VALID_SALE_PRICE_METRIC']=='1']
    metrics={'rows':len(rows),'columns':len(columns),'coverage_start':min(r['TRANSACTION_DATE'] for r in rows),'coverage_end':max(r['TRANSACTION_DATE'] for r in rows),'sales_records':len(sales),'distinct_sales_transaction_numbers':len({r['TRANSACTION_NUMBER'] for r in sales}),'median_sale_price_per_sqft':statistics.median(prices),'off_plan_share':sum(r['IS_OFFPLAN_EN']=='Off-Plan' for r in sales)/len(sales),'ready_share':sum(r['IS_OFFPLAN_EN']=='Ready' for r in sales)/len(sales)}
    for k,v in {'rows':159223,'columns':41,'coverage_start':'2026-01-01','coverage_end':'2026-09-21','sales_records':119549,'distinct_sales_transaction_numbers':119526}.items():check(metrics[k]==v,'Source '+k)
    check(round(metrics['median_sale_price_per_sqft'],2)==1716.79,'Source median')
    check(round(metrics['off_plan_share']*100,2)==68.18 and round(metrics['ready_share']*100,2)==31.82,'Source shares')
    area_labels=collections.defaultdict(set)
    for r in rows: area_labels[r['AREA_EN'].casefold()].add(r['AREA_EN'])
    cases={k:sorted(v) for k,v in area_labels.items() if len(v)>1}
    parsed={}
    for p in PROJECT.rglob('*'):
        if p.is_file() and '.pbi' not in p.parts and (p.suffix in ['.json','.pbip','.pbir','.pbism'] or p.name=='.platform'):
            try: parsed[p]=read(p)
            except Exception as ex:errors.append(f'{p.relative_to(ROOT)}: {ex}')
    theme=ROOT/'powerbi/dubai_real_estate_theme.json';parsed[theme]=read(theme)
    pages=REPORT/'definition/pages'
    page_names=['executive_overview','market_trends','area_intelligence','property_pricing']
    check(read(pages/'pages.json')['pageOrder']==page_names,'Exactly four ordered pages')
    check(sorted(p.parent.name for p in pages.glob('*/page.json'))==sorted(page_names),'No extra pages')
    counts={}; bindings=[]
    for name in page_names:
        p=read(pages/name/'page.json');check(p['width']/p['height']==16/9,name+' aspect ratio')
        visuals=[v for path,v in parsed.items() if path.name=='visual.json' and path.parent.parent.parent.name==name]
        counts[p['displayName']]=dict(collections.Counter(v['visual']['visualType'] for v in visuals))
        expected={'cardVisual':8 if name=='executive_overview' else 4,'slicer':5 if name=='executive_overview' else 3 if name=='market_trends' else 4,'pageNavigator':1}
        for typ,n in expected.items():check(counts[p['displayName']].get(typ,0)==n,f'{name}: {typ} count')
        for v in visuals:
            pos=v['position'];check(pos['x']>=0 and pos['y']>=0 and pos['x']+pos['width']<=1280 and pos['y']+pos['height']<=720,name+': bounds '+v['name'])
            def fields(o):
                if isinstance(o,dict):
                    for typ in ['Measure','Column']:
                        if typ in o and isinstance(o[typ],dict):
                            f=o[typ];entity=f.get('Expression',{}).get('SourceRef',{}).get('Entity')
                            if entity:bindings.append((entity,f['Property'],typ))
                    for x in o.values():fields(x)
                elif isinstance(o,list):
                    for x in o:fields(x)
            fields(v)
    fact=MODEL/'tables/FactTransactions.tmdl';text=fact.read_text(encoding='utf-8-sig')
    measures=re.findall(r"^\tmeasure '([^']+)'",text,re.M)
    old=git('show','a63223c:'+str(fact.relative_to(ROOT)).replace('\\','/'))
    check(text[:text.index('\t/// Source transaction number')]==old[:old.index('\t/// Source transaction number')],'Existing measure definitions changed')
    check(len(measures)==21 and len(set(measures))==21,'21 unique measures reused')
    check(not re.search(r'SUM\s*\([^)]*\[TRANS_VALUE\]',text,re.I),'Prohibited market SUM')
    cols={p.stem:set(re.findall(r"^\tcolumn (?:'([^']+)'|(\S+))",p.read_text(),re.M)) for p in (MODEL/'tables').glob('*.tmdl')}
    cols={t:{a or b for a,b in cs} for t,cs in cols.items()}
    for t,n,k in bindings:check(n in (measures if k=='Measure' and t=='FactTransactions' else cols.get(t,set())),f'Unresolved {k}: {t}.{n}')
    for col in ['TRANSACTION_VALUE_BAND','PROPERTY_SIZE_BAND']:check('sortByColumn: '+col+'_SORT' in text,'Missing band sort '+col)
    check(len(cols['FactTransactions'])==43 and len(cols['DimDate'])==8,'Model column counts')
    changed=[p for p,h in baseline['protected_sha256'].items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
    allowed_prefix='powerbi/Dubai_Real_Estate_Intelligence/'
    unexpected=[p for p in changed if not p.startswith(allowed_prefix)]
    check(not unexpected,'Protected prior-stage files changed: '+str(unexpected))
    # Verify existing Executive visual content except the necessary navigation space.
    for path,v in parsed.items():
        rel=str(path.relative_to(ROOT)).replace('\\','/')
        if '/executive_overview/visuals/' in rel and rel in baseline['protected_sha256']:
            oldv=json.loads(git('show','a63223c:'+rel))
            a=dict(v);b=dict(oldv);a.pop('position');b.pop('position')
            check(a==b,'Executive content changed beyond layout: '+rel)
    # Public schema validation with existing cache read-only; new schemas stay local.
    import requests
    from jsonschema.validators import validator_for
    from referencing import Registry,Resource
    from referencing.jsonschema import DRAFT7
    unavailable=[];validated=[];cache={}
    def retrieve(uri):
        if uri in cache:return cache[uri]
        key=hashlib.sha256(uri.encode()).hexdigest()+'.json';p=HERE.parent/'schemas'/key
        if p.exists(): obj=read(p)
        else:
            r=requests.get(uri,timeout=30);r.raise_for_status();obj=r.json()
        cache[uri]=Resource.from_contents(obj,default_specification=DRAFT7);return cache[uri]
    registry=Registry(retrieve=retrieve)
    failed_uris={}
    for p,obj in parsed.items():
        uri=obj.get('$schema')
        if not uri:continue
        if uri in failed_uris:unavailable.append(str(p.relative_to(ROOT)));continue
        try:
            schema=retrieve(uri).contents
            validator_for(schema)(schema,registry=registry.with_resource(uri,retrieve(uri))).validate(obj)
            validated.append(str(p.relative_to(ROOT)))
        except requests.HTTPError as ex:
            if ex.response.status_code==404:failed_uris[uri]='HTTP 404';unavailable.append(str(p.relative_to(ROOT)))
            else:errors.append(str(ex))
        except Exception as ex:errors.append(f'Schema {p.relative_to(ROOT)}: {str(ex)[:600]}')
    after=sha(SOURCE);expected=baseline['protected_sha256'][str(SOURCE.relative_to(ROOT)).replace('\\','/')]
    check(before==after==expected,'Source hash changed')
    result={'checked_utc':datetime.now(timezone.utc).isoformat(),'passed':not errors,'errors':errors,'source_metrics':metrics,'source_sha256_before':expected,'source_sha256_after':after,'source_unchanged':before==after==expected,'source_case_variants':cases,'page_visual_counts':counts,'dax_measures':measures,'new_measures':0,'schema_validated_count':len(validated),'schema_unavailable_files':unavailable,'schema_unavailable_uris':failed_uris,'protected_files_checked':len(baseline['protected_sha256']),'changed_baseline_files':changed,'unexpected_protected_changes':unexpected,'tracked_diff':git('diff','--name-only'),'scope':'Local structural/schema validation and independent CSV recalculation; live Desktop evidence is separate.'}
    save('stage11_validation.json',result)
    print(json.dumps({k:result[k] for k in ['passed','errors','source_metrics','page_visual_counts','schema_validated_count','schema_unavailable_uris','source_unchanged','unexpected_protected_changes']},indent=2))
    raise SystemExit(bool(errors))

if __name__=='__main__':main()
