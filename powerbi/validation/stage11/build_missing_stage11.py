"""Add only inspected-missing Stage 11 definitions; never regenerate existing pages."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROJECT = ROOT / 'powerbi/Dubai_Real_Estate_Intelligence'
REPORT = PROJECT / 'Dubai_Real_Estate_Intelligence.Report'
PAGES = REPORT / 'definition/pages'
BASE = PAGES / 'executive_overview'
SCHEMA = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json'
NAV_NAMES = ['executive_overview', 'market_trends', 'area_intelligence', 'property_pricing']
COLORS = {'navy':'#192D3A','teal':'#147D83','gold':'#AD823E','muted':'#5E6E78','bg':'#F3F5F6'}

def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def save_new(path, obj):
    text = json.dumps(obj, indent=2, ensure_ascii=False) + '\n'
    if path.exists():
        if read(path) == obj: return
        raise RuntimeError(f'Preserving existing file; inspect before repair: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
def lit(value):
    if isinstance(value,bool): value='true' if value else 'false'
    elif isinstance(value,int): value=f'{value}L'
    else: value="'"+str(value).replace("'","''")+"'"
    return {'expr':{'Literal':{'Value':value}}}
def fill(color): return {'solid':{'color':lit(color)}}
def field(table, name, measure=False, alias=False):
    return {'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Source' if alias else 'Entity':table}},'Property':name}}
def projection(table,name,measure=False,active=False):
    p={'field':field(table,name,measure),'queryRef':table+'.'+name,'nativeQueryRef':name}
    if active:p['active']=True
    return p
def position(x,y,w,h,z): return dict(x=x,y=y,width=w,height=h,z=z,tabOrder=z)
def source_visual(name): return read(BASE/'visuals'/name/'visual.json')
def title(v,text):
    v['visual']['visualContainerObjects']['title'][0]['properties'].update(show=lit(True),text=lit(text),fontSize=lit(11))
def base_visual(sample,name,x,y,w,h,z=10000):
    v=copy.deepcopy(source_visual(sample));v['$schema']=SCHEMA;v['name']=name;v['position']=position(x,y,w,h,z)
    v.pop('filterConfig',None)
    return v
def write_visual(page,v):save_new(PAGES/page/'visuals'/v['name']/'visual.json',v)
def text(page,name,content,x,y,w,h,size=10,color='muted',bold=False):
    v=base_visual('text_platform_subtitle',name,x,y,w,h,1000)
    v['visual']['objects']['general'][0]['properties']['paragraphs']=[{'textRuns':[{'value':content,'textStyle':{'fontFamily':'Segoe UI','fontSize':f'{size}pt','fontWeight':'bold' if bold else 'normal','color':COLORS[color]}}]}]
    write_visual(page,v)
def card(page,name,measure,x,template='kpi_sales_records'):
    v=base_visual(template,name,x,208,299,76)
    v['visual']['query']={'queryState':{'Data':{'projections':[projection('FactTransactions',measure,True)]}}}
    v['visual']['objects']['label'][0]['properties']['text']=lit(measure)
    value=v['visual']['objects']['value'][0]
    value['properties'].pop('labelDisplayUnits',None);value['properties'].pop('labelPrecision',None)
    v['visual']['objects']['value']=[value]
    if measure!='Top Area by Sales Records':
        precision=2 if ('Share' in measure or '%' in measure or 'Price' in measure) else 0
        v['visual']['objects']['value'].append({'properties':{'labelDisplayUnits':lit(1),'labelPrecision':lit(precision)},'selector':{'metadata':'FactTransactions.'+measure}})
    write_visual(page,v)
def slicer(page,name,column,x,w=299):
    v=base_visual('slicer_area',name,x,128,w,64,5000)
    v['visual']['query']={'queryState':{'Values':{'projections':[projection('FactTransactions',column,False,True)]}}}
    labels={'AREA_EN':'Area','PROP_TYPE_EN':'Property type','PROP_SB_TYPE_EN':'Property subtype','IS_OFFPLAN_EN':'Off-plan / ready','TRANSACTION_VALUE_BAND':'Transaction value band'}
    title(v,labels[column]);write_visual(page,v)
def chart(page,name,caption,table,column,measures,x,y,w,h,kind='barChart',category_sort=False):
    sample='chart_monthly_sales' if kind=='lineChart' else 'chart_property_mix'
    v=base_visual(sample,name,x,y,w,h,20000)
    v['visual']['visualType']=kind
    q={'Category':{'projections':[projection(table,column,False,True)]},'Y':{'projections':[projection('FactTransactions',m,True) for m in measures]}}
    q['Tooltips']={'projections':[projection('FactTransactions',m,True) for m in ['Sales Records','Distinct Sales Transaction Numbers','Median Sale Price per Sqft','Off-Plan Share'] if m not in measures]}
    v['visual']['query']={'queryState':q,'sortDefinition':{'sort':[{'field':field(table,column) if category_sort else field('FactTransactions',measures[0],True),'direction':'Ascending' if category_sort else 'Descending'}]}}
    v['visual']['objects']['legend']=[{'properties':{'show':lit(len(measures)>1),'position':lit('Bottom'),'fontSize':lit(9)}}]
    v['visual']['objects']['labels']=[{'properties':{'show':lit(kind!='lineChart'),'fontSize':lit(9)}}]
    # Allow theme colors to distinguish multiple series.
    if len(measures)>1:v['visual']['objects'].pop('dataPoint',None)
    title(v,caption)
    return v
def topn(v,column,n):
    f=copy.deepcopy(source_visual('chart_top10_areas')['filterConfig'])
    blob=json.dumps(f).replace('AREA_EN',column).replace('FilterTop10AreasBySalesRecords','FilterTopStage11Rows')
    f=json.loads(blob)
    f['filters'][1]['filter']['From'][0]['Expression']['Subquery']['Query']['Top']=n
    v['filterConfig']=f
def minimum_sample(v):
    v['filterConfig']={'filters':[{'name':'Minimum30ValidSalePriceRecords','field':field('FactTransactions','Valid Sale Price Records',True),'type':'Advanced','filter':{'Version':2,'From':[{'Name':'f','Entity':'FactTransactions','Type':0}],'Where':[{'Condition':{'Comparison':{'ComparisonKind':2,'Left':field('f','Valid Sale Price Records',True,True),'Right':{'Literal':{'Value':'30L'}}}}}]},'howCreated':'User'}]}
def nonblank(v,column):
    v['filterConfig']={'filters':[{'name':'NonblankBedrooms','field':field('FactTransactions',column),'type':'Advanced','filter':{'Version':2,'From':[{'Name':'f','Entity':'FactTransactions','Type':0}],'Where':[{'Condition':{'Not':{'Expression':{'In':{'Expressions':[field('f',column,False,True)],'Values':[[{'Literal':{'Value':'null'}}]]}}}}}]},'howCreated':'User'}]}
def table(page,name,caption,measures,x,y,w,h):
    v=base_visual('chart_property_mix',name,x,y,w,h,25000)
    v['visual']['visualType']='tableEx'
    v['visual']['query']={'queryState':{'Values':{'projections':[projection('FactTransactions','AREA_EN')]+[projection('FactTransactions',m,True) for m in measures]}},'sortDefinition':{'sort':[{'field':field('FactTransactions','Sales Records',True),'direction':'Descending'}]}}
    v['visual']['objects']={'grid':[{'properties':{'gridVertical':lit(False),'gridHorizontal':lit(False),'rowPadding':lit(3)}}],'columnHeaders':[{'properties':{'fontSize':lit(9),'wordWrap':lit(True)}}],'values':[{'properties':{'fontSize':lit(9)}}],'total':[{'properties':{'totals':lit(False)}}]}
    title(v,caption);write_visual(page,v)
def navigator(page):
    v={'$schema':SCHEMA,'name':'stage11_page_navigation','position':position(24,86,1232,28,4000),'visual':{'visualType':'pageNavigator','objects':{
      'pages':[{'properties':{'showByDefault':lit(True),'showHiddenPages':lit(False),'showTooltipPages':lit(False)}}],
      'layout':[{'properties':{'orientation':lit(2),'cellPadding':lit(8)}}],
      'shape':[{'properties':{'tileShape':lit('rectangle')}}],
      'text':[{'properties':{'show':lit(True)}},{'properties':{'fontSize':lit(10),'fontFamily':lit('Segoe UI'),'fontColor':fill(COLORS['navy']),'horizontalAlignment':lit('center')},'selector':{'id':'default'}},{'properties':{'fontColor':fill('#FFFFFF'),'bold':lit(True)},'selector':{'id':'selected'}}],
      'fill':[{'properties':{'show':lit(True)}},{'properties':{'fillColor':fill('#FFFFFF'),'transparency':lit(0)},'selector':{'id':'default'}},{'properties':{'fillColor':fill(COLORS['teal']),'transparency':lit(0)},'selector':{'id':'selected'}}],
      'outline':[{'properties':{'show':lit(False)}}]},'visualContainerObjects':{'title':[{'properties':{'show':lit(False)}}],'background':[{'properties':{'show':lit(False)}}],'visualHeader':[{'properties':{'show':lit(False)}}]}}}
    write_visual(page,v)
def page(name,display,subtitle,kpis,slicers,footer):
    if (PAGES/name/'page.json').exists():raise RuntimeError(f'Page already exists; inspect and preserve: {name}')
    obj=copy.deepcopy(read(BASE/'page.json'));obj['name']=name;obj['displayName']=display
    save_new(PAGES/name/'page.json',obj)
    text(name,'stage11_title',display,24,16,880,38,22,'navy',True)
    text(name,'stage11_subtitle',subtitle,24,57,880,25,11)
    text(name,'stage11_coverage','Data through 21 September 2026',925,23,331,26,11,'teal',True)
    text(name,'stage11_partial','September 2026 is a partial month.',925,56,331,26,10,'gold')
    text(name,'stage11_footer',footer,24,680,1232,28,9)
    for i,m in enumerate(kpis):card(name,'stage11_kpi_'+str(i+1),m,24+i*311,'kpi_top_area' if m=='Top Area by Sales Records' else 'kpi_sales_records')
    width=(1232-12*(len(slicers)-1))/len(slicers)
    for i,col in enumerate(slicers):slicer(name,'stage11_slicer_'+str(i+1),col,24+i*(width+12),width)
    navigator(name)
def interactions(name):
    path=PAGES/name/'page.json';p=read(path)
    allv=[read(f) for f in (PAGES/name/'visuals').glob('*/visual.json')]
    data=[v for v in allv if v['visual']['visualType'] not in ['textbox','pageNavigator']]
    sources=[v for v in data if v['visual']['visualType']!='cardVisual']
    p['visualInteractions']=[{'source':s['name'],'target':t['name'],'type':'NoFilter' if t['visual']['visualType']=='slicer' and s['visual']['visualType']!='slicer' else 'DataFilter'} for s in sources for t in data if s['name']!=t['name']]
    path.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')

def main():
    page('market_trends','Market Trends','Dubai Property Sales Activity | 2026 YTD',
         ['Sales Records','Previous Month Sales Records','MoM Sales Record Growth %','Off-Plan Share'],['AREA_EN','PROP_TYPE_EN','IS_OFFPLAN_EN'],
         'September is partial. MoM compares the latest selected month with the full previous month. No forecast. Market value is excluded.')
    specs=[('monthly_sales','Monthly Sales Activity',['Sales Records'],'lineChart'),('monthly_mix','Monthly Off-Plan vs Ready',['Off-Plan Sales Records','Ready Sales Records'],'clusteredColumnChart'),('monthly_price','Monthly Median Sale Price per Sqft',['Median Sale Price per Sqft'],'lineChart'),('monthly_residential','Monthly Residential Sales',['Residential Sales Records'],'columnChart')]
    for i,(name,caption,measures,kind) in enumerate(specs):write_visual('market_trends',chart('market_trends',name,caption,'DimDate','Year Month',measures,24+(i%2)*622,300+(i//2)*188,610,176,kind,True))

    page('area_intelligence','Area Intelligence','Sales Activity and Sale Price per Sqft by DLD Area',
         ['Top Area by Sales Records','Sales Records','Median Sale Price per Sqft','Off-Plan Share'],['AREA_EN','PROP_TYPE_EN','IS_OFFPLAN_EN','TRANSACTION_VALUE_BAND'],
         'Pricing bars require at least 30 valid sale price records per area. Source labels and outliers are retained. September is partial.')
    v=chart('area_intelligence','area_top15','Top 15 Areas by Sales Records','FactTransactions','AREA_EN',['Sales Records'],24,300,398,364);topn(v,'AREA_EN',15);write_visual('area_intelligence',v)
    v=chart('area_intelligence','area_median','Area Median Price per Sqft | n >= 30','FactTransactions','AREA_EN',['Median Sale Price per Sqft'],438,300,398,176);minimum_sample(v);write_visual('area_intelligence',v)
    table('area_intelligence','area_activity_price','Sales Activity vs Median Price per Sqft',['Sales Records','Median Sale Price per Sqft'],852,300,404,176)
    table('area_intelligence','area_detail','Area Detail | sorted by Sales Records',['Sales Records','Distinct Sales Transaction Numbers','Off-Plan Sales Records','Ready Sales Records','Off-Plan Share','Median Sale Price per Sqft','Average Sale Price per Sqft'],438,492,818,172)

    page('property_pricing','Property & Pricing','Dubai Property Segment and Pricing Analysis',
         ['Sales Records','Residential Share','Median Sale Price per Sqft','Valid Sale Price Records'],['PROP_TYPE_EN','PROP_SB_TYPE_EN','IS_OFFPLAN_EN','TRANSACTION_VALUE_BAND'],
         'Bedrooms: nonblank source values only; 0 includes studios. Price metrics use valid Sales records. Outliers retained. Market value excluded.')
    specs=[('property_mix','Property Type Sales Mix','PROP_TYPE_EN','Sales Records',False),('property_subtypes','Top 10 Property Subtypes','PROP_SB_TYPE_EN','Sales Records',False),('transaction_bands','Transaction Value Bands','TRANSACTION_VALUE_BAND','Sales Records',True),('size_bands','Property Size Bands','PROPERTY_SIZE_BAND','Sales Records',True),('bedrooms','Bedroom Analysis','BEDROOM_COUNT','Sales Records',True),('type_price','Median Sale Price per Sqft by Type','PROP_TYPE_EN','Median Sale Price per Sqft',False)]
    for i,(name,caption,col,measure,ordered) in enumerate(specs):
        v=chart('property_pricing',name,caption,'FactTransactions',col,[measure],24+(i%3)*416,300+(i//3)*188,400,176,'barChart',ordered)
        if name=='property_subtypes':topn(v,col,10)
        if name=='bedrooms':nonblank(v,col)
        write_visual('property_pricing',v)

    # Stage 10 compatibility edit: reserve one navigation row, keeping every
    # existing visual and binding. Charts keep their original bottom edge.
    navpath=BASE/'visuals/stage11_page_navigation/visual.json'
    if not navpath.exists():
        for path in (BASE/'visuals').glob('*/visual.json'):
            v=read(path)
            if v['visual']['visualType']!='textbox':
                v['position']['y']+=32
                if v['visual']['visualType'] not in ['cardVisual','slicer']:v['position']['height']-=32
                path.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
        navigator('executive_overview')
    metadata=read(PAGES/'pages.json');metadata['pageOrder']=NAV_NAMES
    (PAGES/'pages.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    for name in NAV_NAMES[1:]:interactions(name)
    print('Created exactly three analytical pages. Added 12 cards, 12 charts, 2 tables, 11 slicers and 4 navigators.')

if __name__=='__main__':main()
