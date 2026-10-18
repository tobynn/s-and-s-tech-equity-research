from pathlib import Path
from urllib.request import urlopen
import argparse,re,html,json,hashlib
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--font-dir',type=Path);args=parser.parse_args()
p=json.loads((ROOT/'data/research_inputs.json').read_text());result=json.loads((ROOT/'model/research_results.json').read_text())
fonts=args.font_dir or Path.home()/'.cache/equity-research-fonts';fonts.mkdir(exist_ok=True,parents=True)
for weight in ['Regular','Bold']:
 f=fonts/f'NanumGothic-{weight}.ttf'
 if not f.exists():f.write_bytes(urlopen(f'https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/NanumGothic-{weight}.ttf').read())
 pdfmetrics.registerFont(TTFont('KR'+('B' if weight=='Bold' else ''),str(f)))
pdfmetrics.registerFontFamily('KR',normal='KR',bold='KRB',italic='KR',boldItalic='KRB')
ink=colors.HexColor('#202C3B');accent=colors.HexColor(p['color']);pale=colors.HexColor('#F0F4F8');grid=colors.HexColor('#DCE4EB')
styles={
 'body':ParagraphStyle('body',fontName='KR',fontSize=9.4,leading=15.7,spaceAfter=8,wordWrap='CJK',textColor=ink),
 'h1':ParagraphStyle('h1',fontName='KRB',fontSize=23,leading=33,spaceAfter=12,wordWrap='CJK',textColor=accent),
 'h2':ParagraphStyle('h2',fontName='KRB',fontSize=14,leading=21,spaceBefore=15,spaceAfter=9,keepWithNext=True,wordWrap='CJK',textColor=accent),
 'h3':ParagraphStyle('h3',fontName='KRB',fontSize=11,leading=17,spaceBefore=10,spaceAfter=7,keepWithNext=True,wordWrap='CJK',textColor=accent),
 'cell':ParagraphStyle('cell',fontName='KR',fontSize=8,leading=11.8,wordWrap='CJK',textColor=ink),
 'head':ParagraphStyle('head',fontName='KRB',fontSize=8,leading=12,wordWrap='CJK',textColor=colors.white),
 'small':ParagraphStyle('small',fontName='KR',fontSize=8,leading=12.5,spaceAfter=6,wordWrap='CJK',textColor=colors.HexColor('#596A7B'))}
def inline(s):
 s=html.escape(s.replace('−','-').replace('–','-').replace('—','-'))
 def link(m):
  label,url=m.groups();return f'<link href="{url}" color="{p["color"]}">{label}</link>' if url.startswith('https://') else label
 s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,s)
 s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s);s=re.sub(r'`([^`]+)`',r'<b>\1</b>',s)
 return s
W=A4[0]-36*mm
def table(lines):
 rows=[]
 for l in lines:
  cells=[x.strip() for x in l.strip().strip('|').split('|')]
  if all(re.fullmatch(r':?-{3,}:?',x) for x in cells):continue
  rows.append(cells)
 n=len(rows[0]);weights=[max(8,min(36,max(len(re.sub(r'\[[^]]+\]\([^)]+\)','',r[i])) for r in rows))) for i in range(n)]
 if n>=6:weights=[22]+[16]*(n-1)
 widths=[W*w/sum(weights) for w in weights]
 tab=Table([[Paragraph(inline(c),styles['head' if j==0 else 'cell']) for c in r] for j,r in enumerate(rows)],colWidths=widths,repeatRows=1,hAlign='LEFT')
 tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),accent),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,pale]),('LINEBELOW',(0,0),(-1,0),.5,accent),('LINEBELOW',(0,1),(-1,-1),.25,grid),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
 return tab
out=ROOT/'report/Equity_Research_Report.pdf';out.parent.mkdir(exist_ok=True)
story=[Spacer(1,25*mm),Paragraph('EQUITY RESEARCH / 2026.10.18',styles['small']),Paragraph(f'{p["name"]}<br/>기업가치 분석',styles['h1']),Paragraph(inline(p['subtitle']),styles['h2']),Spacer(1,12*mm),Paragraph(inline(p['thesis']),styles['body']),Spacer(1,8*mm)]
story.append(table(['|방법|Bear|Base|Bull|','|---|---|---|---|']+[f'|{name}|'+ '|'.join(f'{round(result[c][key]/100)*100:,.0f}원' for c in ['Bear','Base','Bull'])+'|' for name,key in [('DCF','dcf_price'),('PER','per_price'),('RIM','rim_price')]]))
story.extend([Spacer(1,8*mm),Paragraph('평가 대상 2026년 말 / 실제 재무제표 2026년 6월 말',styles['body']),Paragraph('전망은 분석자 시나리오입니다. 참고 주가는 NAVER 일별시세이며 거래소 공식 종가와 미대사 상태입니다. 시장 배수를 임의로 만들지 않았으며 각 방법을 평균하지 않았습니다.',styles['small']),Spacer(1,8*mm),Paragraph('산업 · 기업 · 재무 · 전망 · 비교기업 · PER · RIM · DCF · 민감도 · 투자위험',styles['small']),PageBreak()])
lines=(ROOT/'report/FINAL_REPORT.md').read_text().splitlines();i=0
while i<len(lines):
 l=lines[i].strip();i+=1
 if not l:continue
 if l.startswith('|'):
  block=[l]
  while i<len(lines) and lines[i].strip().startswith('|'):block.append(lines[i].strip());i+=1
  story.extend([table(block),Spacer(1,7)]);continue
 if l.startswith('# '):story.append(Paragraph(inline(l[2:]),styles['h1']));continue
 if l.startswith('## '):story.append(Paragraph(inline(l[3:]),styles['h2']));continue
 if l.startswith('### '):story.append(Paragraph(inline(l[4:]),styles['h3']));continue
 if l.startswith('> '):story.append(Paragraph(inline(l[2:]),styles['small']));continue
 if l.startswith('- '):l='• '+l[2:]
 story.append(Paragraph(inline(l),styles['body']))
def footer(c,d):
 c.saveState();c.setStrokeColor(grid);c.line(18*mm,15*mm,A4[0]-18*mm,15*mm);c.setFillColor(accent);c.setFont('KR',7)
 c.drawString(18*mm,10*mm,f'{p["english"]} / 2026.10.18 / 2026 연말E');c.drawRightString(A4[0]-18*mm,10*mm,str(d.page));c.restoreState()
doc=SimpleDocTemplate(str(out),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=18*mm,bottomMargin=22*mm,title=f'{p["name"]} Equity Research 2026-10-18',author='Equity Research Portfolio')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(out)
