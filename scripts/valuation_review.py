"""Economic assumption review. Reads the existing model; does not reset forecasts.
Money: KRW bn; shares: million; prices: KRW. Stress cases are conditional.
"""
import math

def review(p, r):
 c=p['cases'][r['case']]; a=p['h1']; x=p['review_inputs']; f=r['forecast']; last=f[-1]; br=r['bridge']; shares=br['shares_mn']
 w=c['wacc']; ke=c['ke']; g=c['g']; b=last['end_book']; nc=last['end_netcash']; terminal_nopat=last['nopat']*(1+g)
 cash_proxy=min(max(nc,0),b); residual_book=b-cash_proxy
 # This is a sensitivity, not a reconstruction of operating equity.
 cash_split_ni=residual_book*c['roe']+cash_proxy*p['interest']
 cash_split_roe=cash_split_ni/b
 cash_ri=(cash_split_ni-ke*b)/(ke-g)/(1+ke)**5
 zero_ri_equity=br['book_2026e']+sum(q['pv_ri'] for q in r['rim_schedule'])
 no_excess_tv=terminal_nopat/w/(1+w)**5
 no_excess_equity=r['pv_fcff']+no_excess_tv+br['netcash_2026e']+a['nonop']-a['nci']
 required_equity=p['reference_price']*shares/1000
 required_ev=required_equity-br['netcash_2026e']-a['nonop']+a['nci']
 required_fcff=(required_ev-r['pv_fcff'])*(1+w)**5*(w-g)
 implied_terminal_margin=required_fcff/(last['revenue']*(1+g)*(1-p['tax'])*(1-g/c['roic']))
 factor=min(1,a['ni']/a['group_ni'])
 implied_norm_margin=(p['reference_price']/r['per']*shares/1000-br['netcash_2026e']*p['interest'])/(f[1]['revenue']*(1-p['tax'])*factor)
 margin_drop=x['margin_drop']; extra_capex=x['extra_capex']
 margin_impact=sum(q['revenue']*margin_drop*(1-p['tax'])/(1+w)**i for i,q in enumerate(f[1:],1))
 margin_impact+=last['revenue']*margin_drop*(1-p['tax'])*(1+g)*(1-g/c['roic'])/(w-g)/(1+w)**5
 capex_impact=sum(q['capex']*extra_capex/(1+w)**i for i,q in enumerate(f[1:],1))
 z=dict(terminal_reinvestment_2031=(last['capex']-last['da']+last['delta_nwc'])/last['nopat'],terminal_reinvestment_2032=g/c['roic'],fcff_step_2032=r['terminal_fcff']/last['fcff']-1,
  roe_2031=r['rim_schedule'][-1]['roe'],roe_2032=c['roe'],cash_proxy_2031=cash_proxy,cash_book_share=cash_proxy/b,cash_split_terminal_roe=cash_split_roe,
  rim_no_terminal_ri_price=zero_ri_equity*1000/shares,rim_cash_split_price=(zero_ri_equity+cash_ri)*1000/shares,
  dcf_no_excess_roic_price=no_excess_equity*1000/shares,dcf_excess_roic_value=(r['pv_tv']-no_excess_tv)*1000/shares,
  required_terminal_fcff=required_fcff,required_terminal_margin=implied_terminal_margin,required_per_normal_margin=implied_norm_margin,
  dcf_margin_stress_price=r['dcf_price']-margin_impact*1000/shares,dcf_capex_stress_price=r['dcf_price']-capex_impact*1000/shares,
  explicit_value_per_share=r['pv_fcff']*1000/shares,terminal_value_per_share=r['pv_tv']*1000/shares,netcash_per_share=br['netcash_2026e']*1000/shares,
  nonop_less_nci_per_share=(a['nonop']-a['nci'])*1000/shares,per_terminal_share=(1+c['pergrowth'])**4*(1+g)*r['terminal_pe']/(1+ke)**5/r['per'])
 if p['ticker']=='003230':
  z['overseas_growth_if_domestic_flat']=c['growth'][0]/x['overseas_share_proxy']
 elif p['ticker']=='101490':
  z['eb_exchange_dcf_price']=(r['dcf_equity']+x['eb_carrying_amount'])*1000/(shares+x['eb_exchange_shares_mn'])
  z['euv_required_annual_fcff']=max(required_equity-r['dcf_equity'],0)*(1+w)**5*(w-g)
  for rate in x['euv_fcf_margins']:
   z[f'euv_required_revenue_at_{int(rate*100)}pct']=z['euv_required_annual_fcff']/rate
 elif p['ticker']=='064760':
  z['fee_saving_margin_2027']=x['fee_saving_2027']/f[1]['revenue']
  z['fee_delayed_dcf_price']=r['dcf_price']-x['fee_saving_2027']*(1-p['tax'])/(1+w)*1000/shares
 elif p['ticker']=='005930':
  spend=x['hypothetical_buyback']; removed=spend*1000/p['reference_price']
  z['hypothetical_buyback_shares_mn']=removed
  z['post_buyback_dcf_price']=(r['dcf_equity']-spend)*1000/(shares-removed)
 elif p['ticker']=='000660':
  z['financial_asset_haircut_bn']=(x['volatile_short_assets']+a['nonop'])*x['asset_haircut']
  z['financial_asset_stress_dcf_price']=(r['dcf_equity']-z['financial_asset_haircut_bn'])*1000/shares
  z['adr_fx_100_price_effect']=x['adr_usd_bn']*x['adr_fx_shock']*1000/shares
 for v in z.values():assert math.isfinite(v)
 assert abs(sum(z[k] for k in ['explicit_value_per_share','terminal_value_per_share','netcash_per_share','nonop_less_nci_per_share'])-r['dcf_price'])<1e-6
 assert z['dcf_margin_stress_price']<r['dcf_price'] and z['dcf_capex_stress_price']<r['dcf_price']
 assert (r['dcf_price']-z['dcf_no_excess_roic_price'])*(c['roic']-w)>=-1e-7
 return z

def review_text(p,r,d,table,num,pct,px):
 c=p['cases'][r['case']];x=p['review_inputs'];s=p['h1'];f=r['forecast']
 original_table=table
 table=lambda headers,rows: original_table(headers,rows)+'\n'
 terminal='### [장기 수익률과 현금 축적 점검]\n\n'
 terminal+=table(['점검 항목','2031E / 기존 경로','2032E / 성숙 가정'],[['영업 재투자율',pct(d['terminal_reinvestment_2031']),pct(d['terminal_reinvestment_2032'])],['지배주주 ROE',pct(d['roe_2031']),pct(d['roe_2032'])]])
 terminal+=f'2032년 FCFF는 2031년 대비 **{pct(d["fcff_step_2032"])}** 변한다. 성장률 g만큼 증가하는 경로와 다를 수 있다. 이는 투자액·마진 경로에서 성숙 ROIC 기반 재투자로 전환하기 때문이다. 장기 투자수익률과 재투자율의 관계를 먼저 확인하고 이 전환을 자연스러운 연속 성장으로 설명하지 않는다. [방법론 M02]({next(q[3] for q in p["sources"] if q[0]=="M02")})\n\n'
 terminal+=f'2031년 말 순현금 대용액은 자본의 **{pct(d["cash_book_share"])}**다. 기존 RIM의 성숙 ROE {pct(c["roe"])}는 이 현금을 포함한 전체 자본에 적용된다. 현금이 세후 {pct(p["interest"])}만 벌면 같은 ROE를 유지하려면 영업자산의 추가 수익이 필요하다. 다음 표는 이 부담을 분리한다.\n\n'
 terminal+=table(['RIM 장기 가정','조건부 주당가치','해석'],[['전체 자본에 기존 성숙 ROE',px(r['rim_price']),'기존 Base 입력의 결과'],['2032년부터 ROE = 자기자본비용',px(d['rim_no_terminal_ri_price']),'명시기간 후 추가 초과수익 0'],['순현금·잔여 장부자본 수익률 분리',px(d['rim_cash_split_price']),f'현금 {pct(p["interest"])} / 잔여 자본 {pct(c["roe"])}']])
 terminal+=f'현금 분리식: C = min(max(2031년 말 순현금,0),2031년 말 자본), NI_2032 = (B-C) × 성숙 ROE + C × 세후 현금수익률. 여기에서 도출한 전체 ROE는 **{pct(d["cash_split_terminal_roe"])}**다. 이후 자본과 각 부분이 g로 함께 증가한다고 가정해 RI를 자본화한다. 순현금은 차입금 차감 후 금액이며 B-C는 영업자본의 대용 구분이다. 관계기업·투자자산과 영업부채를 계정별 분리한 실제 영업자본이 아니므로 이 값을 새 확정 RIM으로 채택하지 않았다. 음의 terminal RI는 현금을 낮은 수익률로 계속 보유하는 조건의 비용이다. 초과현금 즉시 배당·재투자 대안은 별도 정책 경로가 필요하다. 세 RIM을 평균하지 않는다.\n'
 reverse='### [참고가격 역산과 독립성 점검]\n\n'
 reverse+='DCF·RIM·이론 PER는 할인모형이라는 공통 기반을 가진다. 특히 이론 PER는 배당가능이익의 할인값이고 RIM도 같은 clean-surplus 조건에서 DDM과 일치한다. 세 값의 근접을 세 개의 독립적인 증거로 세지 않는다. 실제 peer 가격·동일 시점 정상 EPS를 확보한 상대가치 검증은 별도 보완 항목으로 유지한다.\n\n'
 reverse+=table(['DCF 가치 구성','원/주'],[['2027~2031 FCFF 현재가치',px(d['explicit_value_per_share'])],['2032년 이후 잔존가치 현재가치',px(d['terminal_value_per_share'])],['연말 순현금',px(d['netcash_per_share'])],['비영업 자산 - 비지배지분',px(d['nonop_less_nci_per_share'])]])
 reverse+=table(['단일 가정 점검','주당가치','고정한 조건'],[['2032년 ROIC = WACC',px(d['dcf_no_excess_roic_price']),'명시기간·g·연말 현금 고정'],[f'2027년 이후 영업마진 {pct(x["margin_drop"])}p 하락',px(d['dcf_margin_stress_price']),'매출·투자·WACC·ROIC 고정; terminal 마진도 하락'],[f'2027~2031 CAPEX {pct(x["extra_capex"])} 증가',px(d['dcf_capex_stress_price']),'D&A·매출·terminal ROIC 고정; 추가 수익 없음']])
 reverse+=f'기존 DCF와 ROIC=WACC DCF의 차이는 **{px(d["dcf_excess_roic_value"])}**로 장기 초과수익 가정의 기여분이다. 고정된 terminal NOPAT에서 ROIC=WACC이면 TV=NOPAT_2032/WACC가 된다. 명시기간이나 성장 전환이 다른 별도 사업 시나리오의 값으로 사용하지 않는다. CAPEX 스트레스는 추가 투자에도 매출·잔존가치의 보상이 없는 비용 충격이다. 실제 증설 투자는 D&A·수율·출하량을 함께 재추정해야 한다.\n\n'
 reverse+=table(['참고가격을 연말 가격으로 고정한 역산','필요 조건'],[['필요 2032년 FCFF(십억원)',num(d['required_terminal_fcff'])],['필요 2032년 영업이익률',pct(d['required_terminal_margin'])],['이론 PER 고정 시 필요 정상화 영업이익률',pct(d['required_per_normal_margin'])]])
 reverse+='역산은 2026-10-16 공급사 참고가격이 2026년 말에도 같다고 둔 조건 비교다. 관측일의 시장이 실제로 이 가정을 가격에 반영했다고 단정하지 않는다. DCF는 명시기간 FCFF·연말 현금·자산·ROIC·g·할인율을 고정하고 terminal FCFF와 마진만 푼다. 필요 FCFF = [참고가격×주식수/1,000 - 연말 순현금 - 비영업 자산 + 비지배지분 - 명시기간 FCFF PV] × (1+WACC)^5 × (WACC-g). 마진은 이를 2032년 매출×(1-세율)×(1-g/ROIC)로 나눈다. 음수나 100% 초과가 나오면 해당 고정조건에서 영업마진으로 설명하기 어렵다는 신호다. PER 역산은 이론 배수·정상 이자수익을 고정한다. 두 역산을 새 전망으로 넣지 않는다.\n\n'
 reverse+=f'이론 PER 값 중 성숙기 분배가능이익의 현재가치 비중은 **{pct(d["per_terminal_share"])}**다. 현재 정상 EPS를 정확히 잡아도 성장 기간·성숙 ROE·요구수익률의 근거가 약하면 이 배수는 충분히 검증되지 않는다.\n\n'
 special='### [기업 고유 가정의 수치 점검]\n\n'
 if p['ticker']=='003230':
  special+=f'2027년 전체 매출 성장률 {pct(c["growth"][0])}를 국내 매출 보합으로 설명하려면 해외 매출은 **{pct(d["overseas_growth_if_domestic_flat"])}** 성장해야 한다. 2026년 해외 비중의 대용치로 H1 {pct(x["overseas_share_proxy"])}를 쓴 항등식(전체 성장률/해외 비중)이다. 지역별 출하·가격·환율을 검증한 회사 가이던스가 아니다. 국내가 성장하면 요구되는 해외 성장률은 낮아지고 국내가 감소하면 높아진다. 중국 공장 CAPEX를 넣는 것과 해외 재주문을 확보하는 것은 서로 다른 확인 항목이다. 상단 마진 스트레스는 운송·판촉·초기 가동비가 판매 증가를 상쇄할 때의 비용 부담을 보여준다.\n'
 elif p['ticker']=='101490':
  special+=f'미교환 DCF {px(r["dcf_price"])}에서 잔여 {x["eb_exchange_shares_mn"]*1e6:,.0f}주 전부 교환 시 분모와 사채 장부금액을 함께 조정한 DCF는 **{px(d["eb_exchange_dcf_price"])}**다. 지분가치에 사채 장부금액 {num(x["eb_carrying_amount"])}을 되돌리고 경제적 주식수에 {x["eb_exchange_shares_mn"]:.6f}백만주를 더한다. 교환은 자기주식 인도로 새 현금이 들어오지 않는다. 부채 제거와 자기주식 처분의 합산 효과이며 이자를 포함한 미래 손익·세금은 고정한 국소 민감도다. 6월 이후 교환이 모두 확인된 현재 주식수라는 뜻은 아니다.\n\n'
  special+=f'참고가격이 기존 사업 DCF보다 높은 차이를 모두 신규 사업으로 설명하고 2027~2031년 추가 현금흐름을 0으로 두면, 2032년부터 필요한 **추가 연간 FCFF는 {num(d["euv_required_annual_fcff"])}십억원**이다. 2032년 이후 이 추가 FCFF가 g로 증가하는 조건이다. 이를 예시 FCFF 마진 20%·30%로 나누면 추가 매출은 각각 **{num(d["euv_required_revenue_at_20pct"])}·{num(d["euv_required_revenue_at_30pct"])}십억원**이다. 두 마진은 상업화 수익성 자료가 없는 상태의 역산 가정이다. 증설·초기 손실을 앞당겨 반영하면 필요한 후속 수익은 더 커진다. 이 가격 차이를 EUV 매출이나 기술 승인 증거로 전환하지 않는다.\n'
 elif p['ticker']=='064760':
  special+=f'Base에 포함한 2027년 판매지원비 절감 {num(x["fee_saving_2027"])}십억원은 같은 해 매출의 **{pct(d["fee_saving_margin_2027"])}p**다. 절감분이 1년 지연되고 2028년 이후 경로는 같으면 2027년 세후 현금흐름 {num(x["fee_saving_2027"]*(1-p["tax"]))}십억원의 현재가치를 잃어 DCF는 **{px(d["fee_delayed_dcf_price"])}**다. 계약 종료 예정을 부인하는 전망이 아니라 일정 민감도다. 기술도입료는 계속 비용에 남는다. H1 수수료의 단순 연율화 5.978십억원을 반올림한 6.0이므로, 향후 매출에 2%를 곱한 절감액과는 구분한다. 계약 적용 대상 매출과 전체 Solid SiC 매출을 같다고 가정하지 않았다.\n'
 elif p['ticker']=='005930':
  special+=f'연말에 추가 {num(x["hypothetical_buyback"])}십억원을 참고가격으로 보통주 매입해 소각·경제적 유통량 감소가 완료된다고 가정하면 감소 주식수는 **{num(d["hypothetical_buyback_shares_mn"],3)}백만주**, DCF는 **{px(d["post_buyback_dcf_price"])}**다. 현금과 지분가치를 같은 금액 차감하고 분모도 함께 줄였다. 이것은 발표된 실제 집행액의 전사가 아니며 연말의 일회성 가정이다. 매입 시점·집행가격·세금·거래비용과 향후 이자수익 변화는 계산하지 않았다. 이론가치 이하 매입이 주당가치를 높이는 항등식의 효과다. 보통·우선주 가치 배분은 동등 경제권 근사이며 실제 종류주식 할인은 해결하지 않는다.\n'
 elif p['ticker']=='000660':
  special+=f'가격변동 위험이 있는 단기투자자산 {num(x["volatile_short_assets"])}와 별도 비영업 자산 {num(s["nonop"])}에 {pct(x["asset_haircut"])} 가치조정을 적용하면 감소 지분가치는 {num(d["financial_asset_haircut_bn"])}십억원, DCF는 **{px(d["financial_asset_stress_dcf_price"])}**다. 현금성 예금 전체를 위험자산으로 처리하지 않았다. 조정률은 세율이나 관측 가격 하락률이 아닌 합성 가치 민감도이며 세금을 추가로 중복 차감하지 않는다. 단기자산 손실이 발생해도 영업현금흐름·이자수익은 고정한 국소 점검이다.\n\n'
  special+=f'ADR 조달 USD {x["adr_usd_bn"]}bn의 원화 환산율이 100원 변하면 연말 현금·자본은 {num(x["adr_usd_bn"]*x["adr_fx_shock"])}십억원, DCF 주당가치는 **±{px(d["adr_fx_100_price_effect"])}** 변한다. 환율이 움직일 때 전사 해외 매출·비용도 같게 변한다고 가정하지 않은 조달액 환산만의 효과다. 실제 납입 환율·발행비·투자 집행이 확인되면 1,400원 가정을 교체한다. 조달금의 CAPEX 사용을 차감할 때에는 새 영업자산의 수익도 함께 계산해야 하므로 전액 유휴현금 보유와 투자 확대를 같은 현금에 중복 적용하지 않는다.\n'
 evidence='### [가정별 증거와 변경 조건]\n\n'
 evidence+=table(['판단할 가정','확인한 자료·성격','현재 모델 연결','추가 확인·변경 조건'],p['evidence_review'])
 evidence+='자료가 회사 공시인지, 회사가 재게시한 보도인지, 분석자 가정인지 구분했다. 숫자로 식별되지 않은 고객 승인·제품 가격·점유율은 정량 프리미엄으로 넣지 않는다. 공시로 관찰 가능한 변수가 달라지면 해당 입력을 바꾸고 세 평가식을 다시 계산한다.\n'
 return dict(terminal=terminal,reverse=reverse,special=special,evidence=evidence)
