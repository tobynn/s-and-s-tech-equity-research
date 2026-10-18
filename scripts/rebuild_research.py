"""Rebuild the report and numerical schedules from one dated input file.
Usage: python scripts/rebuild_research.py
All money is KRW billion, shares in millions, per-share money in KRW.
"""
from pathlib import Path
import json,csv,math,re,shutil
from valuation_review import review, review_text
ROOT=Path(__file__).resolve().parents[1]
def mdtable(headers,rows):
 return '\n'.join(['| '+' | '.join(map(str,headers))+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'
def num(x,d=1):return '미공개' if x is None else f'{x:,.{d}f}'
def pct(x):return f'{x*100:,.1f}%'
def px(x):return f'{round(x/100)*100:,.0f}원'
def justified_per(growth,high_roe,stable_g,stable_roe,ke,years=5):
 payout=1-growth/high_roe;terminal=(1-stable_g/stable_roe)/(ke-stable_g)
 return sum((1+growth)**(i-1)*payout/(1+ke)**i for i in range(1,years+1))+(1+growth)**(years-1)*(1+stable_g)*terminal/(1+ke)**years
def csvout(path,rows):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def calculate(p,case,wacc_override=None,g_override=None):
 a=p['h1'];c=p['cases'][case];ke=c['ke'];wacc=wacc_override or c['wacc'];g=g_override if g_override is not None else c['g']
 shares=a['shares']+p['addshares'];nc0=a['cash']+a['liquid']-a['debt']-a['leases'];rev=c['rev26'];nci=a['nci'];factor=min(1,a['ni']/a['group_ni'])
 # Operating taxes apply to EBIT, never to financing/non-recurring income.
 h2rev=rev-a['rev'];h2op=rev*c['margin'][0]-a['op'];h2nopat=h2op*(1-p['tax']);h2interest=nc0*p['interest']*.5
 h2ni=h2nopat*factor+h2interest
 h2da=c['da'][0]-a['da'];h2capex=c['capex'][0]-a['capex'];nwc26=rev*c['nwc'][0];h2dnwc=nwc26-a['nwc'];h2fcff=h2nopat+h2da-h2capex-h2dnwc
 nc26=nc0+h2fcff+h2interest-p['h2div']-p['h2buyback']+p['capital'];b26=a['equity']+h2ni-p['h2div']-p['h2buyback']+p['capital']
 rows=[dict(year=2026,revenue=rev,op_margin=c['margin'][0],ebit=rev*c['margin'][0],tax=p['tax'],nopat=rev*c['margin'][0]*(1-p['tax']),da=c['da'][0],capex=c['capex'][0],nwc=nwc26,delta_nwc=None,fcff=None,ni=a['ni']+h2ni,eps=(a['ni']+h2ni)*1000/shares,begin_book=None,dividend=None,end_book=b26,end_netcash=nc26)]
 book=b26;cash=nc26;nwc=nwc26
 for i,y in enumerate(range(2027,2032),1):
  rev*=1+c['growth'][i-1];op=rev*c['margin'][i];nopat=op*(1-p['tax']);newnwc=rev*c['nwc'][i];dnwc=newnwc-nwc;fcff=nopat+c['da'][i]-c['capex'][i]-dnwc
  interest=cash*p['interest'];ni=nopat*factor+interest;div=ni*c['payout'];newbook=book+ni-div;cash+=fcff+interest-div
  rows.append(dict(year=y,revenue=rev,op_margin=c['margin'][i],ebit=op,tax=p['tax'],nopat=nopat,da=c['da'][i],capex=c['capex'][i],nwc=newnwc,delta_nwc=dnwc,fcff=fcff,ni=ni,eps=ni*1000/shares,begin_book=book,dividend=div,end_book=newbook,end_netcash=cash))
  book=newbook;nwc=newnwc
 pvfcff=sum(r['fcff']/(1+wacc)**i for i,r in enumerate(rows[1:],1));terminal_nopat=rows[-1]['nopat']*(1+g);terminal_fcff=terminal_nopat*(1-g/c['roic']);tv=terminal_fcff/(wacc-g);pvtv=tv/(1+wacc)**5;ev=pvfcff+pvtv;dcfeq=ev+nc26+a['nonop']-nci
 # RI_2032 uses B_2031 (the beginning book for 2032). No extra growth factor.
 rim=[]
 for i,r in enumerate(rows[1:],1):
  charge=ke*r['begin_book'];ri=r['ni']-charge;rim.append(dict(year=r['year'],begin_book=r['begin_book'],ni=r['ni'],coe=ke,charge=charge,ri=ri,pv_ri=ri/(1+ke)**i,end_book=r['end_book'],roe=r['ni']/r['begin_book']))
 tri=(c['roe']-ke)*book;triv=tri/(ke-g);pvtri=triv/(1+ke)**5;rimeq=b26+sum(r['pv_ri'] for r in rim)+pvtri
 # Independent DDM identity check on exactly the same clean-surplus path.
 term_equity=book+triv;ddm=sum(r['dividend']/(1+ke)**i for i,r in enumerate(rows[1:],1))+term_equity/(1+ke)**5
 hg=c['pergrowth'];rh=c['perroe'];per_payout=1-hg/rh;term_payout=1-g/c['roe'];terminal_pe=term_payout/(ke-g)
 per=sum((1+hg)**(i-1)*per_payout/(1+ke)**i for i in range(1,6))+(1+hg)**4*(1+g)*terminal_pe/(1+ke)**5
 normni=rows[1]['revenue']*c['permargin']*(1-p['tax'])*factor+nc26*p['interest'];normeps=normni*1000/shares;perprice=normeps*per
 bridge=dict(netcash_h1=nc0,h2_revenue=h2rev,h2_ebit=h2op,h2_nopat=h2nopat,h2_da=h2da,h2_capex=h2capex,h2_delta_nwc=h2dnwc,h2_fcff=h2fcff,h2_interest=h2interest,h2_ni=h2ni,h2_dividend=p['h2div'],h2_buyback=p['h2buyback'],capital=p['capital'],netcash_2026e=nc26,book_2026e=b26,shares_mn=shares)
 return dict(case=case,forecast=rows,rim_schedule=rim,bridge=bridge,pv_fcff=pvfcff,pv_tv=pvtv,ev=ev,terminal_fcff=terminal_fcff,dcf_equity=dcfeq,dcf_price=dcfeq*1000/shares,tv_share=pvtv/ev,rim_equity=rimeq,rim_price=rimeq*1000/shares,rim_pv_terminal=pvtri,rim_identity_error=rimeq-ddm,normalized_eps=normeps,per=per,per_price=perprice,terminal_pe=terminal_pe,per_payout=per_payout,terminal_payout=term_payout)
def report(p,rs):
 b=rs['Base'];a=p['h1'];c=p['cases']['Base'];br=b['bridge'];rows=b['forecast'];s=p['sources'];links={x[0]:x[3] for x in s}; diagnostic=review(p,b); extra=review_text(p,b,diagnostic,mdtable,num,pct,px)
 def cite(i):return f'[{i}]({links[i]})'
 t=[]
 def add(x):t.append(x.strip()+'\n')
 add(f'# [{p["name"]} 기업분석 | 실적에서 주당가치까지]')
 add(f'> {p["subtitle"]}\n\n발간·모델 수정일 2026-10-18 | 정보 확인일 2026-10-18 | 실제 재무제표 2026-06-30 | 평가 대상 시점 2026-12-31E | 금액 십억원, 주가 원/주')
 add('## [01. 투자 판단과 예상주가]')
 add(p['thesis'])
 add(mdtable(['방법','Bear','Base','Bull','계산의 역할'],[[n,px(rs['Bear'][k]),px(b[k]),px(rs['Bull'][k]),role] for n,k,role in [('DCF','dcf_price','중심 시나리오: 투자 이후 영업현금흐름'),('PER','per_price','정상화 EPS와 이론 배수의 교차검증'),('RIM','rim_price','장부자본과 초과 ROE의 지속성')]]))
 add(f'본 보고서의 중심 산출값은 **DCF Base {px(b["dcf_price"])}**, DCF 시나리오 범위는 **{px(rs["Bear"]["dcf_price"])}~{px(rs["Bull"]["dcf_price"])}**다. 모두 2026년 말 조건부 적정주가이며, 12개월 후 거래가격의 통계적 예측이나 증권사 컨센서스가 아니다. 각 시나리오의 확률은 추정하지 않았다. 전망의 매출·마진·투자 경로가 성립할 때의 값이다.')
 add(f'가격 비교에는 5개 기업 모두 **2026-10-16 NAVER 일별시세 참고 종가**를 사용했다. 이 기업의 참고가는 **{p["reference_price"]:,.0f}원**, DCF Base와의 차이는 **{pct(b["dcf_price"]/p["reference_price"]-1)}**다. 배당을 제외한 연말 시나리오 가격차이며 확률적 기대수익률이 아니다. KRX 공식 종가와의 대사는 완료되지 않았고, 일부 종목은 Yahoo의 같은 날짜 값과 다르다. 공급사 가격을 섞지 않았다. 시가총액·매수 등급은 제시하지 않는다. '+cite('PX01'))
 add('세 방법은 할인율·성장·분배 가정을 공유한다. PER와 RIM은 독립적인 시장 증거로 세지 않으며 평균 목표가를 만들지 않는다. 소형기업의 시장가격이 기본 사업 가치와 다르면 미확인 신규 사업의 가치나 이익 지속성에 관한 추가 가정을 확인해야 한다. 해당 가격 차이만으로 시장가격이 틀렸다고 결론 내리지 않는다.')
 add(f'핵심 반증은 {p["risks"][0][1]}이다. 다음 실적에서는 이 조건과 현금 회수를 먼저 확인한다. 핵심 실적의 원자료는 {cite("S01")}에서 확인할 수 있다.')
 add(f'**[이번 점검의 판단]** 장기 초과 ROIC를 0으로 둔 DCF는 {px(diagnostic["dcf_no_excess_roic_price"])}다. 순현금의 낮은 수익률을 분리한 RIM 민감도는 {px(diagnostic["rim_cash_split_price"])}로 기존 RIM과 차이가 난다. 기존 Base의 산식과 숫자는 보존하고, 이 차이를 조건부 가치의 핵심 한계로 명시했다. 같은 이론 PER를 고정해 참고가격을 설명하려면 정상 영업이익률 {pct(diagnostic["required_per_normal_margin"])}가 필요하다. 이는 신규 전망이나 관측 시장 프리미엄이 아니다. 자세한 전환 가정과 기업별 수치 점검은 09·11절을 따른다.')
 add('## [02. 평가기준일·자료기준일·가정 버전]')
 add(mdtable(['항목','이번 보고서 기준','처리 방식'],[['발간·모델 버전','2026-10-18 / research-v3','보고서·CSV·Excel·PDF 동일 입력'],['정보 확인일','2026-10-18','원자료 발표일과 분리'],['재무상태 기준일','2026-06-30A','실제 현금·부채·지배주주 자본'],['평가 대상 시점','2026-12-31E','하반기 이익·투자·배당을 연결'],['명시 전망','2026E 및 2027E~2031E','2026년은 실제 H1과 추정 H2'],['잔존가치 시작','2032년','정상 성장·ROIC·ROE 적용'],['참고 종가','2026-10-16 / NAVER 일별시세','공급사별 차이 기록; 거래소 확정값 미대사'],['정량 peer 배수','미사용','동일 시점 정상 EPS·가격 확보 전 미산정']]))
 add('Valuation vintage라는 표현은 평가에 쓴 정보 묶음과 추정치의 버전을 뜻할 때 사용한다. 독자에게는 평가기준일·자료기준일·가정 버전으로 적는 편이 명확하다. 기술 상업화 단계, 프리미엄, 할인율은 각각 별도 개념이다. 이번 문서의 발간일을 과거 자료의 발표일로 바꾸지 않는다.')
 add('2026년 말 적정주가는 현 시점 가치와 날짜가 다르다. 6월 말 자본에 하반기 전체 이익을 더하는 계산은 연말 평가를 위한 것이다. 연말 현금에 2026년 전체 FCFF를 다시 더하지 않으며, 연말 DCF에는 2027년 이후 현금흐름만 할인한다. 실제 연말 공시 전까지 현금·자본 연결표의 하반기 부분은 분석자 추정이다.')
 add('## [03. 산업 분석과 이익이 결정되는 과정]')
 for para in p['industry']:add(para)
 add('위 문단의 수요·가격·원가 연결은 공개된 사업 특성을 바탕으로 한 분석자의 해석이다. 총주소시장(TAM), 점유율, 고객별 단가가 공개되지 않은 부분에는 임의 숫자를 채우지 않았다. 산업 성장이 회사의 동일 성장률을 보장한다는 가정도 사용하지 않는다.')
 add('## [04. 기업 분석과 사업별 확인 항목]')
 add(mdtable(['사업','수익의 출발점','확인할 항목','모델 처리'],p['businesses']))
 citation_order={'003230':['S03','S03','S04'],'101490':['S04','S01','S01'],'064760':['S03','S02','S02'],'005930':['S02','S02','S03'],'000660':['S02','S01','S02']}[p['ticker']]
 for para,ci in zip(p['company'],citation_order):add(para+' '+cite(ci))
 add('기업 분석의 판단은 다음 순서를 따른다. 제품·사업의 수익원이 무엇인지 확인하고, 판매량·가격·원가·고정비가 손익으로 이어지는 과정을 설명한다. 이후 투자와 운전자본을 차감해 현금 회수를 점검한다. 마지막으로 이 수익이 자본비용을 넘는 기간을 PER와 RIM에 반영한다. 같은 성장 요인을 매출 성장과 별도 프리미엄에 반복 반영하지 않는다.')
 add('## [05. 실제 실적과 재무제표 점검]')
 add(mdtable(['기간','매출','영업이익','순이익(전체)','영업이익률','출처'],[[h[0],num(h[1]),num(h[2]),num(h[3]),pct(h[2]/h[1]),cite(actual_source(p,h[0]))] for h in p['hist']]))
 add('A는 공시 실제치, P는 회사 잠정 발표, E는 분석자 추정이다. 반기·분기와 연간을 같은 길이의 기간으로 비교하지 않는다. 순이익 표는 연결 전체(티씨케이는 별도)이고, RIM은 지배주주 순이익과 자본을 쓴다. 소수점 반올림으로 합계 차이가 생길 수 있다.')
 add(mdtable(['2026H1 기준','값','정의'],[['지배주주 자본',num(a['equity']),'RIM 출발값; 비지배지분 제외'],['비지배지분',num(a['nci']),'DCF 지분가치에서 장부금액 대용 차감'],['현금및현금성자산',num(a['cash']),'현금성 자산 계정'],['포함 단기금융·투자자산',num(a['liquid']),'회사별 원문 범위 확인'],['차입금·사채',num(a['debt']),'이자부 부채'],['추가 차감 리스부채',num(a['leases']),'이미 차입금에 포함된 경우 0'],['순현금',num(br['netcash_h1']),'현금+포함 금융자산-차입금-추가 리스'],['핵심 영업운전자본',num(a['nwc']),'매출채권+재고-매입채무'],['영업현금흐름',num(a['cfo']),'공시 분류 그대로; 배당 분류 주의'],['모델 취득액 기준',num(a['capex']),'공시 PP&E 취득; 회사별 무형 포함 범위 명시'],['기초 경제적 주식수(백만주)',num(a['shares'],6),'자기주식 제외; 삼성 보통+우선']]))
 add(f'순현금은 {num(a["cash"])} + {num(a["liquid"])} - {num(a["debt"])} - {num(a["leases"])} = {num(br["netcash_h1"])}다. 기타금융자산 전체를 현금으로 간주하지 않았다. 비유동 금융자산 별도 가산액은 {num(a["nonop"])}이며 매각세금·실현 가능성은 별도 민감도로 다룬다. '+cite('S01'))
 if p['ticker']=='003230':add('기존 RIM의 연결 자본총계 1,548.3에서 비지배지분 17.470을 빼 지배주주 자본 1,530.797을 확정했다. 기존 숫자를 잠정 proxy로 계속 쓰지 않는다. 주식수는 발행 7,533,015주에서 자기주식 2주를 차감한 7,533,013주다. '+cite('S07'))
 if p['ticker']=='101490':add('교환사채 미교환 기본 조건을 사용한다. 부채 13.868을 순현금에서 차감하고 유통주식 21,075,750주를 분모로 쓴다. 244,504주 전부 교환을 가정할 경우 같은 시점의 사채부채를 자본·현금조정에 되돌리고 분모도 늘려야 한다. 교환 후 주식수만 늘리고 부채를 계속 차감하면 희석을 중복 반영한다. 6월 이후 실제 교환 이력 전부를 대사한 현재 주식수로 주장하지 않는다. '+cite('S03'))
 if p['ticker']=='064760':add('기존 저장소의 H1 영업이익 49.227과 순이익 48.751을 원문 55.404와 48.763으로 수정했다. H1 2026/2025 성장률은 매출 약 26.0%, 영업이익 약 28.9%, 순이익 약 37.3%다. 회사가 별도 재무제표를 작성하므로 연결 기준이라고 표기하지 않는다. '+cite('S01'))
 if p['ticker']=='005930':add('지배주주 자본은 565,064.740이다. 발행 보통 5,846,278,608주와 우선 802,371,203주에서 보통 자기주식 82,086,705주를 빼 경제적 분모 6,566,563,106주를 사용했다. 두 종류 주식의 경제적 권리를 1주 대 1주로 보는 근사값이며 의결권·우선배당·시장 할인은 별도로 평가하지 않았다. 전사 가치를 보통주 수만으로 나누던 방식은 사용하지 않는다. '+cite('S04'))
 if p['ticker']=='000660':add('금융자산의 장부가치를 현금과 구분한다. 포함 단기자산에는 단기투자자산 38,724.378이 있어 가격변동 위험이 있다. 비유동 가산액 92,411.327은 장기투자자산 85,309.524와 장기금융상품 7,101.803의 합이다. 이 금액의 0%·50%·100% 인정 민감도를 함께 읽는다. 금융상품 평가이익을 순이익에 반복 가산하고 자산가치도 더하는 방식은 금지한다. '+cite('S02'))
 add('## [06. 실적 전망과 가정의 근거]')
 for reason in p['reasons']:add(reason)
 add(mdtable(['십억원','2026E','2027E','2028E','2029E','2030E','2031E'],[[label]+[pct(r[key]) if key=='op_margin' else num(r[key]) for r in rows] for label,key in [('매출','revenue'),('영업이익률','op_margin'),('영업이익','ebit'),('지배주주 순이익','ni'),('EPS(원)','eps'),('D&A','da'),('CAPEX','capex'),('핵심 NWC','nwc')]]))
 add(f'정상 세율 {pct(p["tax"])}와 순현금 세후 수익률 {pct(p["interest"])}는 분석자 가정이다. 현재 세법에서 확정된 세율이나 회사 가이던스로 표시하지 않는다. 해외 법인·세액공제·이연법인세·환율 때문에 보고 세율과 다를 수 있다. 2026년 순이익은 H1 실제 지배주주 순이익에 H2의 세후 영업이익과 정상 이자수익을 더한다. 이후 순이익은 세후 영업이익의 지배주주 귀속 추정분과 순현금 수익으로 만든다. 금융상품 평가손익·OCI는 0으로 가정한다. 미래 지배주주 귀속 비율은 반기 지배주주 순이익/반기 전체 순이익으로 추정하되, 비지배지분 손실로 비율이 100%를 넘으면 100%로 제한했다. 미래 자회사별 수익성이 달라질 수 있어 이 비율은 회사 확정치가 아니다.')
 add('매출 전망은 관찰 가능한 실적과 사업 조건을 반영한 집계 경로다. 고객별 계약물량, 정확한 제품별 ASP·수율이 모두 공개된 수량 기반 예산은 아니다. 해당 미공개 수치를 임의로 만들어 정밀한 물량 모델로 포장하지 않았다. 가정별 근거와 실제 확인 조건을 다음 시나리오 표에 남겼다.')
 add(extra['evidence'])
 add('## [07. 비교기업 선정과 프리미엄·할인 근거]')
 add(mdtable(['비교기업','역할','선정 이유','중요한 차이','정량 사용 판정'],p['peers']))
 if p['ticker']=='003230':add('농심과 오리온의 공식 실적·사업 자료를 통해 제품과 해외 사업 범위를 확인했다. '+cite('P01')+' '+cite('P02'))
 if p['ticker']=='064760':add('하나머티리얼즈는 공식 회사개요에 Dry etching용 Silicon electrode·ring과 SiC 제품을 제시한다. 제품 중첩이 정량 후보 선정의 근거이며 현재 시장 배수의 동일성을 뜻하지 않는다. '+cite('P01'))
 if p['ticker']=='101490':add('HOYA의 IT 사업 설명과 Photronics의 제품 설명으로 블랭크 소재와 완성 포토마스크의 공급망 단계를 구분했다. '+cite('S06')+' '+cite('S07'))
 add('정량 peer에 포함하는 절차는 제품과 고객 수요의 일치, 생산설비와 감가상각 부담, 수익 인식과 회계기준, 정상 EPS의 비교 가능성, 가격·추정치의 같은 날짜 여부 순서다. 후보 수를 늘리기 위해 제조 단계가 다른 회사를 넣지 않는다. 이 보고서는 같은 날짜의 라이선스 허용 forward EPS·가격 자료를 확보하지 못했으므로 관측 peer 중앙값과 회귀 프리미엄을 계산하지 않았다. 위 표는 사업 비교와 향후 정량 편입 기준이다.')
 add('프리미엄은 여러 정성 점수에 배수를 임의로 더하는 방식으로 정하지 않는다. 성장률이 높아도 이를 만들기 위한 자본이 많이 필요하면 배당 가능한 이익은 줄어든다. 동일 성장률에서는 자본수익률이 높고 위험이 낮으며 성장 기간이 길수록 이론 PER가 높아진다. 이 관계로 배수 차이를 설명하고, 시장이 실제로 해당 배수를 지불한다는 주장과 구분한다. '+cite('M01'))
 add(mdtable(['프리미엄 후보','먼저 반영할 항목','배수에서 다시 더하지 않을 항목','확인 조건'],[['수요·판매 확대','Forecast 매출·마진','같은 성장의 일괄 가산','반복 출하·재주문·회수'],['기술·인증','성장 기간·초기 비용','발표만으로 가산','양산 승인·수율·품질비용'],['자본효율','ROIC·재투자·지속 ROE','마진 개선을 재가산','투자 후 현금전환'],['고객·제품 집중','Bear 판매·마진','근거 없는 고정 할인','거래처·제품 다변화'],['규모·유동성','요구수익률 범위','중소형이라는 이유만의 정밀 할인','금융시장 자료로 검증 후 조정']]))
 add('## [08. PER: 정상화 EPS와 배수의 계산]')
 add(f'첫 단계는 2027E 매출 {num(rows[1]["revenue"])}에 중간 사이클 영업이익률 {pct(c["permargin"])}를 적용해 정상 이익을 구하는 것이다. 보고 이익과 정상 이익은 다르다. 세금·주주 귀속·순현금 수익을 반영한 정상화 EPS는 **{num(b["normalized_eps"],0)}원**이다. 반복되지 않는 평가이익과 일시적 세금 환입을 제외한다. 현금과 비영업 투자자산은 PER 결과에 별도로 더하지 않는다. 이는 DCF의 자산 가산과 계산 범위가 다르다.')
 add(f'둘째 단계는 5년 동안의 EPS 성장률 {pct(c["pergrowth"])}와 증분 ROE {pct(c["perroe"])}를 적용한다. 성장기 배당 가능 비율은 1 - 성장률/ROE = **{pct(b["per_payout"])}**다. 이후 성장률 {pct(c["g"])}와 성숙 ROE {pct(c["roe"])}를 적용하면 성숙 배당 가능 비율은 **{pct(b["terminal_payout"])}**다. 이는 성장 투자 후 이론상 분배 가능한 이익 비중이며 회사의 실제 배당 계획과 다르다.')
 add('계산식: EPS_t = EPS_2027 × (1+성장기 성장률)^(t-1). 2026년 말 가치 = 2027~2031년 배당가능액의 현재가치 합 + [2032년 정상 EPS × 성숙 배당가능비율 / (자기자본비용-성숙 성장률)]의 현재가치. 이 값을 2027년 정상 EPS로 나누면 forward PER가 된다. 미래 기간 수와 적용 배수를 모두 공개하므로 임의 프리미엄율이 필요하지 않다.')
 add(f'Base 정당화 PER는 **{b["per"]:.2f}배**, 정상화 EPS는 **{num(b["normalized_eps"],0)}원**, 곱한 주당가치는 **{px(b["per_price"])}**다. 이 배수는 관측된 peer PER가 아니다. 성장·ROE·요구수익률 가정으로 도출한 이론 배수다. 회사별 정량 peer 자료가 확보되면 그 분포 안에서 해당 배수가 왜 다른지 대조한다.')
 add(mdtable(['적용 PER(민감도)','6배','8배','10배','12배','15배','20배'],[['정상화 EPS 적용 주가']+[px(b['normalized_eps']*x) for x in [6,8,10,12,15,20]]]))
 add(mdtable(['초과성장 지속기간','3년','5년(Base)','7년'],[['정당화 PER(배)']+[num(justified_per(c['pergrowth'],c['perroe'],c['g'],c['roe'],c['ke'],n),2) for n in [3,5,7]]]))
 add(mdtable(['자기자본비용 / 5년 EPS 성장률']+[pct(c['pergrowth']+d) for d in [-.02,0,.02]],[[pct(c['ke']+dk)]+[num(justified_per(c['pergrowth']+dg,c['perroe'],c['g'],c['roe'],c['ke']+dk),2) for dg in [-.02,0,.02]] for dk in [-.01,0,.01]]))
 add('위 두 표는 프리미엄의 원인이 성장 기간인지 요구수익률인지 나눠 보여준다. 같은 성장률도 증분 ROE가 낮으면 재투자가 많이 필요해 배당 가능 비율이 낮아진다. 이 표의 상대 차이는 이론 가정의 효과이며, 실제 peer 대비 관측 프리미엄으로 표현하지 않는다. PER의 한계는 정상화 마진과 초과성장의 기간을 추정해야 한다는 점이다. 저점·고점 EPS를 그대로 사용하면 배수가 뒤집혀 보일 수 있다. 배수와 이익을 동시에 상향하는 시나리오는 동일 원인이 중복 반영됐는지 먼저 확인한다.')
 add('## [09. RIM: 지배주주 자본과 잔여이익]')
 add(f'RIM은 주주가 이미 보유한 자본에 미래 초과이익의 현재가치를 더한다. 6월 말 지배주주 자본 {num(a["equity"])}에서 H2 순이익 {num(br["h2_ni"])}를 더하고 배당 {num(p["h2div"])}·자사주 {num(p["h2buyback"])}를 빼며 신규 납입 {num(p["capital"])}를 더하면 2026E 말 자본 **{num(br["book_2026e"])}**이 된다. OCI와 추가 자본거래는 0인 시나리오다.')
 add('매년 잔여이익 RI_t = 지배주주 순이익_t - 자기자본비용 × 기초 지배주주 자본_t. 기말 자본 = 기초 자본 + 순이익 - 배당. 다음 해 기초 자본은 전년 기말과 연결한다. 전체 순이익을 연결 자본총계와 섞거나 반기 실제 자본에 연간 순이익 전부를 더하지 않는다.')
 add(mdtable(['연도','기초 자본','순이익','ROE','자본비용','RI','RI 현재가치'],[[r['year'],num(r['begin_book']),num(r['ni']),pct(r['roe']),num(r['charge']),num(r['ri']),num(r['pv_ri'])] for r in b['rim_schedule']]))
 add(f'성숙기 ROE {pct(c["roe"])}와 자기자본비용 {pct(c["ke"])}를 사용한다. 2032년 RI는 **(성숙 ROE - 자기자본비용) × 2031년 말 자본**이다. 2031년 말 자본은 이미 2032년 기초 자본이므로 여기에 성장률을 한 번 더 곱하지 않는다. 이후 RI가 장기 성장률 {pct(c["g"])}로 증가한다고 두어 (자기자본비용-g)로 자본화한다. Base RIM 주당가치는 **{px(b["rim_price"])}**다.')
 add(f'같은 이익·배당·청산가치 경로를 배당할인식으로 계산한 값과의 차이는 {b["rim_identity_error"]:.8f}십억원이다. 이 일치 여부는 clean-surplus 계산과 기간 연결을 점검하는 검증이다. 경제적 가정이 맞다는 검증은 아니다. 성숙 ROE가 자본비용과 같아지면 terminal RI는 0이 된다.')
 add(extra['terminal'])
 add('## [10. DCF: 매출에서 자유현금흐름까지]')
 add('FCFF = EBIT × (1-정상 세율) + 감가상각·상각 - CAPEX - 핵심 운전자본 증가. NWC는 매출채권+재고-매입채무로 정의한다. 다른 영업성 자산·부채와 선수금·성과급·세금 납부 시차는 별도 추정하지 않아 실제 현금흐름과 차이가 날 수 있다. CAPEX 전망에는 공정 유지·증설·무형 및 신규 리스 대체투자에 필요한 총투자 가정을 포함한다. 미래 신규 리스 투자 누락은 DCF를 높일 수 있어 투자 민감도에서 확인한다.')
 add(mdtable(['십억원','2027E','2028E','2029E','2030E','2031E'],[[label]+[num(r[key]) for r in rows[1:]] for label,key in [('EBIT','ebit'),('NOPAT','nopat'),('D&A','da'),('CAPEX','capex'),('NWC 증가','delta_nwc'),('FCFF','fcff')]]))
 add(f'2026년 말부터 각 연도 말까지 1~5년의 연말 할인 방식을 쓴다. Base WACC는 {pct(c["wacc"])}다. 이는 재현 가능한 시나리오 할인율이며, 같은 날짜의 국채금리·베타·ERP를 모두 확보해 추정한 시장 CAPM 결과로 주장하지 않는다. 자기자본비용은 {pct(c["ke"])}다. 자본구조가 거의 무차입인 소형기업은 두 값의 차이를 작게 두고, 자본집약도가 높은 반도체 회사는 높은 요구수익률 범위를 점검했다. 별도 임의 규모 프리미엄은 추가하지 않았다.')
 add(f'성숙기 FCFF_2032 = NOPAT_2031 × (1+g) × (1-g/ROIC). Base g는 {pct(c["g"])}이고 성숙 ROIC는 {pct(c["roic"])}다. 성숙기 재투자율은 {pct(c["g"]/c["roic"])}다. 마지막 해 FCF를 그대로 영구 연장해 성장투자를 누락하지 않는다. 성숙 ROIC가 WACC로 수렴할 때 성장률 상승의 가치 효과가 작아지는지도 확인한다. '+cite('M02'))
 add(mdtable(['DCF 계산','Base 십억원'],[['명시기간 FCFF 현재가치',num(b['pv_fcff'])],['잔존가치 현재가치',num(b['pv_tv'])],['영업가치(EV)',num(b['ev'])],['2026E 말 순현금 가산',num(br['netcash_2026e'])],['비영업 금융자산 별도 가산',num(a['nonop'])],['비지배지분 장부금액 대용 차감',num(a['nci'])],['지배주주 지분가치',num(b['dcf_equity'])],['경제적 주식수(백만주)',num(br['shares_mn'],6)],['주당가치(원)',num(b['dcf_price'],0)]]))
 add(f'EV에서 잔존가치 비중은 **{pct(b["tv_share"])}**다. 이 비중이 높으면 단기 이익 개선보다 장기 ROIC·g·할인율에 결론이 크게 움직인다. 비지배지분은 시장가치를 확보하지 못해 장부가치를 대용했으며, 금융자산 가산액은 매각세금 전 장부금액이다. 장부금액을 즉시 회수 가능한 현금으로 단정하지 않는다.')
 add('## [11. 시나리오·민감도와 결과 차이]')
 add(mdtable(['주요 가정','Bear','Base','Bull'],[[label]+[pct(p['cases'][z][k]) for z in ['Bear','Base','Bull']] for label,k in [('WACC','wacc'),('자기자본비용','ke'),('영구성장률','g'),('성숙 ROIC','roic'),('성숙 ROE','roe'),('PER 정상 영업마진','permargin')]]))
 gs=[max(.005,c['g']-.005),c['g'],c['g']+.005];ws=[c['wacc']-.01,c['wacc'],c['wacc']+.01]
 add(mdtable(['DCF WACC / g']+[pct(x) for x in gs],[[pct(w)]+[px(calculate(p,'Base',w,x)['dcf_price']) for x in gs] for w in ws]))
 add('위 민감도는 전체 Base 매출·마진·투자와 연말 현금을 고정하고 WACC와 terminal g만 바꾼 부분 민감도다. Bear/Bull은 여러 사업 조건이 함께 바뀌므로 이 표의 모서리 값과 같지 않다. RIM에서 성숙 ROE=자기자본비용인 경우 잔여이익의 terminal은 0이 되고, 현재 높은 이익이 얼마나 오래 남는지가 결론을 좌우한다.')
 if a['nonop']:
  add(mdtable(['비영업 금융자산 인정률','0%','50%','100%'],[['DCF 주당가치']+[px((b['dcf_equity']-a['nonop']+a['nonop']*q)*1000/br['shares_mn']) for q in [0,.5,1]]]))
  add('인정률 표는 매각 확률이 아니다. 자산 실현 가능성·가격 하락·세금에 대한 별도 가격 민감도다. PER은 정상 수익만 평가하고 비영업 자산을 별도 가산하지 않으므로 DCF와 차이가 난다.')
 add('DCF와 RIM의 차이는 영업 재투자·회계자본·금융자산의 범위 및 terminal 수익률 가정에서 발생한다. PER의 정상 마진과 분배 가능한 성장 경로도 DCF 집계 이익 경로와 다르다. 차이가 크다는 이유로 중간값을 목표가로 택하지 않는다. 본 표는 가정의 차이를 드러내는 용도다.')
 add(extra['reverse'])
 add(extra['special'])
 add('## [12. 투자위험과 다음 확인 자료]')
 add(mdtable(['위험','관찰할 악화 조건','변경 입력','갱신 모델'],p['risks']))
 add('다음 정기 공시에서 확인할 순서는 실제 손익, 지배주주 자본과 주식수, 현금흐름·CAPEX·운전자본, 제품·고객 관련 설명이다. 실적이 바뀌면 Forecast를 먼저 바꾸고 같은 이익을 PER·RIM·DCF로 전달한다. 가격 데이터만 바뀌면 상승여력과 시장 PER만 갱신하며 기업 실적 전망을 자동으로 바꾸지 않는다.')
 add('보고서의 약한 근거를 숫자 자릿수로 보완하지 않는다. 고객별 비공개 수익성, 시장 CAPM 입력, 동일 날짜 forward peer 자료, 실제 연말 환율·자본거래는 현재 추정의 한계다. 이런 항목은 공개 사실과 분리해 입력 파일에 남긴다. 신규 공시가 나오면 과거 판단을 보존한 채 입력 버전을 추가한다.')
 add('## [13. 계산 재현과 검증 기록]')
 add('단일 입력은 `data/research_inputs.json`이다. `python scripts/rebuild_research.py`로 실적·전망·현금/자본 연결표·RIM·결과 CSV와 본문을 다시 만든다. `model/Equity_Research_Model.xlsx`에는 동일 입력에서 만든 편집 가능한 수식이 들어 있다. 엑셀 생성 스크립트는 `scripts/build_model.mjs`이며 artifact-tool이 설치된 환경에서 실행한다. PDF는 `scripts/build_report_pdf.py`로 본문에서 재생성한다. `scripts/valuation_review.py`가 장기 수익률·현금 분리·가격 역산·기업별 민감도를 계산하고 `model/valuation_review.json`과 CSV로 남긴다. Excel의 Diagnostics·Special Cases는 같은 계산을 수식으로 재현한다. 이전 파일은 `archive/`와 Git 커밋 이력에 보존하며 현재 결과의 근거로 사용하지 않는다.')
 add(mdtable(['검증','수행 내용'],[['출처 1차 점검','반기 원문 계정·단위·귀속·주식수 대사'],['출처 2차 점검','요약표와 재무제표 및 주석 교차 확인'],['기간 검증','H1 실제 + H2 추정 = 2026E; DCF는 2027년부터'],['자본 검증','지배주주 자본의 clean-surplus 연결'],['모델 검증','Python 독립 계산과 Excel 결과 대조'],['RIM 검증','동일 배당 경로 DDM과의 항등식 확인'],['민감도 검증','WACC 상승 시 DCF 하락과 시나리오 결과 비교'],['경제적 가정 검증','장기 재투자 전환·현금 분리·가격 역산·기업별 자본거래 민감도'],['문서 검증','5개 동일 목차·표·모델 결과·PDF 렌더 확인']]))
 add('이 검증은 산식·입력 전사·문서 일치를 확인하는 작업이다. 공개되지 않은 회사 내부 예산이나 투자 결과를 확정하지 않는다. 참고 종가는 NAVER 일별시세로 통일했으며 공급사 차이는 `data/price_crosscheck.csv`에 남겼다. KRX 공식 종가 검증으로 표시하지 않는다.')
 add('### [2026H1에서 2026년 말로 이어지는 계산표]')
 add(mdtable(['하반기·연말 항목','Base 십억원'],[[label,num(br[key])] for label,key in [('H2 매출','h2_revenue'),('H2 EBIT','h2_ebit'),('H2 NOPAT','h2_nopat'),('H2 D&A','h2_da'),('H2 CAPEX','h2_capex'),('H2 NWC 증가','h2_delta_nwc'),('H2 FCFF','h2_fcff'),('H2 정상 이자수익','h2_interest'),('H2 지배주주 순이익','h2_ni'),('H2 배당','h2_dividend'),('H2 자사주 매입','h2_buyback'),('신규 납입 자금','capital'),('연말 순현금','netcash_2026e'),('연말 지배주주 자본','book_2026e')]]))
 if p['ticker']=='000660':add('신주 조달액은 USD 26.5071bn × 1,400원/USD = 37,109.94십억원의 환산 시나리오다. 발행 비용 0, 조달액 전액 보유를 가정한다. 환율·비용·자금 집행이 바뀌면 현금과 자본을 동시에 고친다. 2026E 경제적 주식수는 711.0755 + 17.79 = 728.8655백만주다. '+cite('S02'))
 if p['ticker']=='005930':add('H2 현금배당 30,000은 발표된 분기 환원 계획을 참고한 시나리오이며, 2026년 전체 환원 예상 90,000~110,000 전액을 하반기 확정 집행으로 차감하지 않았다. 추가 자사주 매입은 0인 조건부 계산이다. 실제 매입이 확인되면 현금·자본 감소와 경제적 주식수 감소를 함께 반영해야 한다. '+cite('S05'))
 add('## [14. 출처와 자료 사용 범위]')
 for sid,title,pub,url,note in s:add(f'- **{sid}** {pub}, {title}. 확인 2026-10-18. {note}. [{title}]({url})')
 add('분석자 추정치는 공시 실제치의 출처를 대신하지 않는다. 본 보고서의 수치 전망, 정상화 세율, 배당, 투자액, 마진, 요구수익률과 성숙 수익률은 입력 파일의 가정이다. 외부 리서치 보고서의 목표주가나 비공개 컨센서스를 복사하지 않았다.')
 return '\n'.join(t)
def actual_source(p,period):
 if period.endswith('P'):return 'S03'
 if 'H1' in period or 'Q2' in period:return 'S01'
 if p['ticker']=='003230':return 'S06' if period=='2023A' else 'S02'
 return {'101490':'S04','064760':'S05','005930':'S06','000660':'S04'}[p['ticker']]
def main():
 p=json.loads((ROOT/'data/research_inputs.json').read_text());rs={case:calculate(p,case) for case in ['Bear','Base','Bull']}
 for r in rs.values():
  assert abs(r['rim_identity_error'])<1e-5
  assert r['bridge']['h2_revenue']>=0 and r['bridge']['h2_capex']>=0 and r['bridge']['h2_da']>=0
  for v in ['dcf_price','rim_price','per_price']:assert math.isfinite(r[v])
 diagnostics={k:review(p,v) for k,v in rs.items()}
 b=rs['Base'];assert calculate(p,'Base',p['cases']['Base']['wacc']+.01)['dcf_price']<b['dcf_price']
 (ROOT/'model').mkdir(exist_ok=True);(ROOT/'report').mkdir(exist_ok=True)
 (ROOT/'model/research_results.json').write_text(json.dumps(rs,ensure_ascii=False,indent=2)+'\n')
 csvout(ROOT/'model/forecast.csv',[dict(case=k,**r) for k,v in rs.items() for r in v['forecast']])
 csvout(ROOT/'model/rim_schedule.csv',[dict(case=k,**r) for k,v in rs.items() for r in v['rim_schedule']])
 csvout(ROOT/'model/cash_equity_bridge.csv',[dict(case=k,**v['bridge']) for k,v in rs.items()])
 csvout(ROOT/'model/valuation_results.csv',[dict(case=k,dcf_price=v['dcf_price'],rim_price=v['rim_price'],per_price=v['per_price'],per=v['per'],normalized_eps=v['normalized_eps'],valuation_date='2026-12-31E',model_version=p['model_version']) for k,v in rs.items()])
 (ROOT/'model/valuation_review.json').write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2)+'\n')
 csvout(ROOT/'model/valuation_review.csv',[dict(case=k,metric=key,value=value) for k,z in diagnostics.items() for key,value in z.items()])
 (ROOT/'report/FINAL_REPORT.md').write_text(report(p,rs))
 readme=ROOT/'README.md'
 if readme.exists() and '\n---\n' in readme.read_text():
  prefix=readme.read_text().split('\n---\n',1)[0];readme.write_text(prefix+'\n---\n\n'+report(p,rs))
 csvout(ROOT/'data/actuals_verified.csv',[dict(period=h[0],revenue_bn=h[1],operating_profit_bn=h[2],net_income_bn=h[3],basis='standalone' if p['ticker']=='064760' else 'consolidated',source_id=actual_source(p,h[0])) for h in p['hist']])
 csvout(ROOT/'data/source_register.csv',[dict(source_id=x[0],title=x[1],publisher=x[2],url=x[3],accessed='2026-10-18',use=x[4]) for x in p['sources']])
 print(p['name'],{k:round(b[k]) for k in ['dcf_price','rim_price','per_price']},'report chars',len(report(p,rs)))
if __name__=='__main__':main()
