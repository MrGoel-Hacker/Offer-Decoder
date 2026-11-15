"""Branded decision report from an immutable saved snapshot; no model or network calls."""
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from pathlib import Path
import math
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, Flowable
from report_legal import LEGAL_SECTIONS

INK, MUTED, GREEN, PALE, LINE = '#102B2B', '#58706F', '#087F68', '#EAF5F0', '#D9E5E0'
WIDTH = A4[0] - 88
FONT_DIR = Path(__file__).parent / 'assets' / 'fonts'
pdfmetrics.registerFont(TTFont('ODBody', str(FONT_DIR / 'Lato-Regular.ttf')))
pdfmetrics.registerFont(TTFont('ODBold', str(FONT_DIR / 'Lato-Bold.ttf')))
pdfmetrics.registerFontFamily('ODBody', normal='ODBody', bold='ODBold', italic='ODBody', boldItalic='ODBold')


def safe(value):
    return escape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(value))).replace('\n', '<br/>')


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else 0
    except (ValueError, TypeError):
        return 0


def money(value, us=False):
    value = number(value)
    digits = str(int(math.floor(abs(value) + .5)))
    if us:
        digits = f'{int(digits):,}'
    elif len(digits) > 3:
        head, tail, groups = digits[:-3], digits[-3:], []
        while head:
            groups.insert(0, head[-2:]); head = head[:-2]
        digits = ','.join(groups + [tail])
    return ('-' if value < 0 else '') + ('$' if us else '₹') + digits


class ReportCanvas(Canvas):
    """Defer footers until the actual page count is known."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved_pages = []

    def showPage(self):
        self.saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        count = len(self.saved_pages)
        for state in self.saved_pages:
            self.__dict__.update(state)
            self.saveState()
            self.setStrokeColor(colors.HexColor(LINE)); self.setLineWidth(.6)
            self.line(44, 47, A4[0]-44, 47)
            self.setFont('ODBody', 7); self.setFillColor(colors.HexColor(MUTED))
            self.drawString(44, 32, f'© {datetime.now(timezone.utc).year} OfferDecoder. All rights reserved in protectable material.')
            self.drawRightString(A4[0]-44, 32, f'{self._pageNumber} / {count}')
            self.setFont('ODBody', 6.6)
            self.drawString(44, 20, 'AI-assisted estimates. Not legal, tax or financial advice. See the final legal-notices page.')
            self.restoreState(); super().showPage()
        super().save()


class PackageBar(Flowable):
    def __init__(self, segments):
        super().__init__(); self.width = WIDTH; self.height = 52; self.segments = segments

    def draw(self):
        total = sum(v for _, v, _ in self.segments) or 1
        x = 0
        for _, value, color in self.segments:
            width = self.width * value / total
            self.canv.setFillColor(colors.HexColor(color)); self.canv.rect(x, 32, width, 14, fill=1, stroke=0); x += width
        for i, (label, value, color) in enumerate(self.segments):
            x = i * self.width / len(self.segments)
            self.canv.setFillColor(colors.HexColor(color)); self.canv.rect(x, 14, 5, 5, fill=1, stroke=0)
            self.canv.setFillColor(colors.HexColor(MUTED)); self.canv.setFont('ODBody', 7.5)
            self.canv.drawString(x+10, 13, f'{value/total:.1%} {label}')


def clause_guidance(flag):
    """Neutral questions; never infer missing amounts, quotations or source pages."""
    lower = str(flag.get('text', '')).lower()
    rules = [
        (r'bond|training|service agreement|service commitment', 'Service commitment / recovery', 'An early-exit or training-recovery condition may affect flexibility and repayment obligations.', 'Please share the full agreement, recovery amount, duration, exceptions and whether repayment reduces with service completed.'),
        (r'claw|repay|joining|signing', 'One-time award / repayment', 'One-time awards may have repayment conditions and should not be treated as recurring monthly salary.', 'What is the repayment period, is recovery gross or net of tax, and is it pro-rated?'),
        (r'notice|termination', 'Notice and transition terms', 'Notice and early-release conditions can affect the timing of your next role.', 'Please confirm employee and employer notice, buyout, approval timelines and early-release options.'),
        (r'compet|solicit|outside work', 'Restrictions and permitted activities', 'The scope of a restriction needs its original wording and local context; this report does not determine enforceability.', 'Which activities, employers, clients, locations and time periods are covered, and what exceptions apply?'),
        (r'variable|performance|payout|bonus', 'Variable-pay conditions', 'Target pay may depend on conditions and timing rather than arriving as dependable monthly cash.', 'What are the payout conditions, payment dates, eligibility rules and historical payout percentages?'),
    ]
    for pattern, title, why, ask in rules:
        if re.search(pattern, lower): return title, why, ask
    return 'Clause to clarify', 'The extraction flags a condition to verify in the original offer; missing scope or context must not be assumed.', 'Please explain this condition, its practical effect and any exceptions, and confirm the agreed wording in writing.'


def render_report(session, result, created_at):
    us = session.get('country') == 'us'
    fmt = lambda value: money(value, us)
    d, tax, inp = result.get('derived', {}), result.get('taxFixed', {}), session.get('input', {})
    flags = [f if isinstance(f, dict) else {'text': str(f), 'source': 'clause'} for f in result.get('flags', [])]
    clauses = [f for f in flags if f.get('source') == 'clause']
    ordered_flags = sorted(flags, key=lambda f: (f.get('source') != 'clause', f.get('level') != 'warn'))
    bonus, joining, equity = [number(d.get(k)) for k in (('bonus','signing','rsus') if us else ('variable','joining','esops'))]
    styles = {}
    for name,size,leading,color,font in [('body',9.3,13.5,INK,'ODBody'),('small',8,11.2,MUTED,'ODBody'),('label',8,11,GREEN,'ODBold'),('title',25,29,INK,'ODBold'),('h2',13,18,INK,'ODBold'),('cardtitle',10.5,14,INK,'ODBold'),('amount',33,40,'#FFFFFF','ODBold'),('light',9,13,'#D0E5DF','ODBody'),('legal',8,10.6,MUTED,'ODBody')]:
        styles[name] = ParagraphStyle(name,fontName=font,fontSize=size,leading=leading,textColor=colors.HexColor(color),spaceAfter=7 if name in ('body','small','legal') else 9,keepWithNext=name in ('h2','cardtitle','label'),splitLongWords=True)
    styles['legalhead'] = ParagraphStyle('legalhead',parent=styles['cardtitle'],fontSize=9.3,leading=12,spaceAfter=3)
    styles['metric'] = ParagraphStyle('metric',parent=styles['h2'],fontSize=16,leading=21)
    styles['legal'].spaceAfter = 5
    def p(text, style='body', markup=False):
        return Paragraph(text if markup else safe(text), styles[style])
    def card(contents, fill=PALE, padding=13):
        t = Table([[contents]],colWidths=[WIDTH],splitInRow=1,cornerRadii=[9]*4)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor(fill)),('BOX',(0,0),(-1,-1),.5,colors.HexColor(LINE)),('LEFTPADDING',(0,0),(-1,-1),padding),('RIGHTPADDING',(0,0),(-1,-1),padding),('TOPPADDING',(0,0),(-1,-1),padding),('BOTTOMPADDING',(0,0),(-1,-1),padding)]))
        return t
    def section(label,title,description):
        return [p(label,'label'),p(title,'title'),p(description,'small'),Spacer(1,9)]
    def table(headers,rows,widths):
        data=[[p(h,'label') for h in headers]]+[[p(str(cell),'small') for cell in row] for row in rows]
        t=Table(data,colWidths=widths,repeatRows=1,splitInRow=1,hAlign='LEFT')
        t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor(PALE)),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#F3F7F5'),colors.white]),('LINEBELOW',(0,0),(-1,-1),.35,colors.HexColor(LINE)),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        return t

    story=section('01 / THE BIG PICTURE','Your offer, at a glance.',' / '.join(filter(None,[session.get('company'),session.get('role')])) or 'Your saved offer report')
    story.append(p(f'{"USA" if us else "India"} / Saved {created_at.strftime("%d %b %Y")} / {"USD" if us else "INR"} / Annualised full-year estimates','small'))
    story += [card([p('BASE SALARY TAKE-HOME PER MONTH' if us else 'ESTIMATED FIXED MONTHLY TAKE-HOME','light'),p(fmt(result.get('monthlyFixed')),'amount'),p('After estimated deductions and taxes. Excludes one-time joining/signing bonus; target variable pay and equity are not dependable monthly cash.','light')],INK,18),Spacer(1,13)]
    metrics=[('FIXED GROSS CASH',d.get('base') if us else result.get('cashGross'),'Annual; before deductions'),('TARGET VARIABLE',bonus,'Annual; conditional'),('ANNUAL EQUITY' if us else 'JOINING BONUS',equity if us else joining,'Before vesting / sale' if us else 'One-time; confirm CTC treatment')]
    mt=Table([[[p(label,'label'),p(fmt(value),'metric'),p(note,'small')] for label,value,note in metrics]],colWidths=[WIDTH/3]*3)
    mt.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F3F7F5')),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story += [mt,Spacer(1,20),p('Three things to know before you decide','h2')]
    insights=[('Plan around recurring cash.',f'The headline annual package is {fmt(result.get("ctc"))}. The saved fixed-pay estimate is {fmt(result.get("monthlyFixed"))} per month; these measure different things.'),('Separate conditional and one-time amounts.',f'Target variable: {fmt(bonus)}; annual equity value: {fmt(equity)}; joining/signing award: {fmt(joining)}. Confirm payout, vesting and repayment conditions.'),('Verify the extracted terms.',str(clauses[0].get('text')) if clauses else 'No clause flag was captured. That is not evidence that the offer contains no restrictive or unusual terms. Read the original agreement.')]
    for i,(title,body) in enumerate(insights,1): story += [KeepTogether([p(f'{i:02d} / {title}','cardtitle'),p(body,'body')]),Spacer(1,6)]
    story += [card([p('HOW TO READ THIS REPORT','label'),p('EXTRACTED = parsed from supplied text or entered by you, not independently verified. CALCULATED = from the saved calculator. ASSUMED = a default or estimate to check. This report is not an actual payslip.','small'),p('Online access lasts up to 90 days. Keep a downloaded copy for your records.','small')]),PageBreak()]

    story += section('02 / FOLLOW THE MONEY','What becomes spendable cash?','Recurring cash, conditional pay and deferred value are separated. Monthly equivalents do not imply a monthly payment.')
    if us:
        segments=[('base cash',max(0,number(d.get('base'))),GREEN),('target bonus',max(0,bonus),'#E5AB49'),('equity',max(0,equity),'#9DAFA8')]
        rows=[('Base salary',fmt(d.get('base')),fmt(number(d.get('base'))/12),'Recurring gross cash'),('Target bonus',fmt(bonus),'-','Conditional; confirm timing'),('Annual RSUs / equity',fmt(equity),'-','Vesting / sale conditions'),('Signing bonus',fmt(joining),'One-time','Confirm repayment terms'),('Employee 401(k)',fmt(d.get('k401')),fmt(number(d.get('k401'))/12),'Employee saving, not extra pay')]
    else:
        benefits=sum(number(d.get(k)) for k in ('employerPF','gratuity','otherNonCash'))
        segments=[('gross cash',max(0,number(result.get('cashGross'))),GREEN),('variable / awards',max(0,bonus+joining+equity),'#E5AB49'),('employer benefits',max(0,benefits),'#9DAFA8')]
        definitions=[('basic','Basic salary','Recurring gross cash'),('hra','HRA','Recurring gross cash'),('specialAndOther','Special / other allowance','Recurring gross cash'),('employerPF','Employer PF','Not bank credit'),('gratuity','Gratuity provision','Not monthly cash'),('otherNonCash','Other non-cash','Not bank credit'),('variable','Target variable','Conditional'),('joining','Joining bonus','One-time; confirm placement'),('esops','Annual ESOP value','Vesting / liquidity conditions')]
        rows=[(label,fmt(d.get(key)),'-' if key in ('variable','joining','esops') else fmt(number(d.get(key))/12),treatment) for key,label,treatment in definitions if number(d.get(key))]
    story += [PackageBar(segments),table(['COMPONENT','ANNUAL','MONTHLY','TREATMENT'],rows or [('No breakdown captured','-','-','Verify the original offer')],[WIDTH*.36,WIDTH*.21,WIDTH*.19,WIDTH*.24]),Spacer(1,12)]
    if not us and joining:
        story += [card([p('VERIFY JOINING-BONUS PLACEMENT','label'),p('This saved calculation treats the joining bonus as part of CTC. If your letter says it is additional to CTC, the fixed-pay calculation needs correction. Do not subtract it twice or rely on an unverified classification.','small')],'#FFF6E7'),Spacer(1,12)]
    if us:
        bt=result.get('taxBase',{})
        deductions=[('Base gross salary',fmt(d.get('base'))),('401(k), base-pay allocation',fmt(bt.get('k401'))),('Federal income tax',fmt(bt.get('federal'))),('State income tax',fmt(bt.get('stateTax'))),('Social Security',fmt(bt.get('ss'))),('Medicare',fmt(bt.get('medicare'))),('Annual base take-home',fmt(result.get('annualTakeHomeFixed')))]
    else:
        deductions=[('Fixed gross cash salary',fmt(result.get('cashGross'))),('Employee PF',fmt(d.get('employeePF'))),('Professional tax',fmt(d.get('profTax'))),('Income tax including cess',fmt(tax.get('totalTax'))),('Annual fixed take-home',fmt(result.get('annualTakeHomeFixed')))]
    story += [p('From gross pay to fixed take-home / CALCULATED','h2'),table(['ANNUAL AMOUNT','VALUE'],deductions,[WIDTH*.7,WIDTH*.3]),Spacer(1,8),p(f'If target variable / equity pays in full, the yearly-average monthly take-home is {fmt(result.get("monthlyWithVariable"))}. This is a scenario, not a promised monthly payslip.','small')]
    if result.get('meta',{}).get('slabsVerifiedAgainst'): story.append(p('Calculator reference recorded with this snapshot: '+str(result['meta']['slabsVerifiedAgainst']),'small'))
    url='https://www.irs.gov/individuals/tax-withholding-estimator' if us else 'https://www.incometax.gov.in/iec/foportal/income-tax-calculator'
    story += [p(f'<link href="{url}" color="{GREEN}">Official tax estimator / calculator</link>','small',True),PageBreak()]

    story += section('03 / READ THE CONDITIONS','The terms worth clarifying.','Clause flags are extracted indicators, not verified quotations or legal conclusions. Numerical flags come from the saved calculation. No source page references are invented.')
    if not ordered_flags: story.append(card([p('No flags captured','cardtitle'),p('No issue was captured in this saved analysis. This does not confirm that the offer is safe, complete or free of restrictions. Ask for all referenced policies and agreements.','body')]))
    for i,flag in enumerate(ordered_flags,1):
        is_clause=flag.get('source')=='clause'
        title,why,ask=clause_guidance(flag) if is_clause else ('From the numbers',str(flag.get('why') or 'Check this feature of the saved compensation calculation.'),str(flag.get('ask') or 'Please confirm the relevant amounts, assumptions and conditions in writing.'))
        if us and not is_clause and re.search(r'rsu|equity|stock',str(flag.get('text','')).lower()):
            title='Equity is conditional, not monthly cash'
            why='Value and availability depend on vesting, market price and liquidity; payroll withholding and net proceeds can differ.'
            ask='What grant valuation, vesting schedule, payroll withholding and sale restrictions apply?'
        contents=[p(f'{i:02d} / {"EXTRACTED CLAUSE FLAG" if is_clause else "CALCULATED FLAG"}','label'),p(title,'cardtitle'),p(flag.get('text',''),'body')]
        if flag.get('letter'): contents.append(p('Captured clause summary (not a verified quotation): '+str(flag['letter']),'small'))
        contents += [p('WHY IT MATTERS: '+why,'small'),p('YOUR QUESTION: '+ask,'body')]
        story += [card(contents,'#F5F8F6'),Spacer(1,10)]
    story += [p('Missing scope, durations or amounts must be checked in the original agreement. This report does not determine enforceability.','small'),PageBreak()]

    story += section('04 / USE THE REPORT','Your next conversation.','Prioritise dependable pay, repayment exposure and flexibility. Get agreed changes in the final written offer.')
    story.append(p('Negotiation priorities','h2'))
    tips=list(dict.fromkeys(str(t) for t in result.get('tips',[]) if t)) or ['Ask for a full compensation and deduction breakdown.','Confirm conditional payments and all referenced employment terms in writing.']
    for i,tip in enumerate(tips,1): story.append(p(f'{i}. {tip}','body'))
    questions=[]
    for flag in ordered_flags:
        question=clause_guidance(flag)[2] if flag.get('source')=='clause' else ('What grant valuation, vesting schedule, payroll withholding and sale restrictions apply?' if us and re.search(r'rsu|equity|stock',str(flag.get('text','')).lower()) else str(flag.get('ask') or ''))
        if question and question not in questions: questions.append(question)
    questions=['Please confirm recurring salary, payroll deductions, bonus timing and whether one-time awards sit inside or outside the headline package.']+questions[:3]
    message='Thank you for the offer. Before I confirm, could you clarify the following in writing?\n\n'+'\n'.join(f'{i}. {q}' for i,q in enumerate(questions,1))+'\n\nPlease include agreed changes in the final written offer. Thank you.'
    story += [Spacer(1,7),p('A message you can send to HR','h2'),card([p(message,'body')]),Spacer(1,15),p('Calculation notes and evidence','h2')]
    input_names={'ctc':'CTC','basic':'Basic','hra':'HRA','employerPF':'Employer PF','gratuity':'Gratuity','variablePay':'Variable','joiningBonus':'Joining bonus','esopsPerYear':'Annual ESOPs','otherNonCash':'Non-cash','employeePF':'Employee PF','profTax':'Professional tax','baseSalary':'Base salary','targetBonus':'Target bonus','signingBonus':'Signing bonus','rsuPerYear':'Annual RSUs','k401':'401(k)','state':'State'}
    input_text=', '.join(f'{input_names.get(key,key)}: {fmt(value) if key not in ("state","gratuityInCTC") else value}' for key,value in inp.items())
    story.append(p('EXTRACTED / ENTERED: '+input_text if inp else 'EXTRACTED / ENTERED: original inputs were not stored.','small'))
    story.append(p(f'CALCULATED: Annual fixed take-home {fmt(result.get("annualTakeHomeFixed"))}; recurring monthly estimate {fmt(result.get("monthlyFixed"))}. Figures reproduce the saved snapshot; the PDF does not recalculate or verify your original offer.','small'))
    assumptions=list(dict.fromkeys(str(v) for v in result.get('assumptions',[]) if v))
    assumptions += [v for v in (result.get('stateNote'),result.get('meta',{}).get('countryNote')) if v and v not in assumptions]
    for value in assumptions: story.append(p('ASSUMED / LIMITATION: '+value,'small'))
    if not us and 'employeePF' not in inp: story.append(p('ASSUMED: Employee PF follows the saved default when not supplied; verify with payroll.','small'))
    if not us and 'profTax' not in inp: story.append(p('ASSUMED: Professional tax follows the saved default, not a verified state-specific payroll schedule.','small'))
    story.append(p('SCOPE: Annualised 12-month estimate. Actual joining-year income, other income, payroll timing and personal circumstances can change the outcome. Bonuses and equity are not promised monthly cash.','small'))
    story.append(p('Tax scope: '+str(result.get('meta',{}).get('regime','Not recorded in this snapshot')),'small'))
    tax_keys=[('taxable','Federal taxable income'),('federal','Federal income tax'),('stateTax','State income tax'),('ss','Social Security'),('medicare','Medicare'),('totalTax','Annual taxes with target bonus / equity')] if us else [('taxable','Taxable fixed-pay income'),('slabTax','Tax before rebate'),('rebate','Rebate / relief'),('cess','Cess'),('totalTax','Annual fixed-pay income tax')]
    story.append(p('ANNUAL TAX DETAIL: '+'; '.join(f'{label}: {fmt(tax.get(key))}' for key,label in tax_keys)+'.','small'))
    story.append(PageBreak())

    story += section('05 / IMPORTANT INFORMATION','Legal notices and permitted use.','OfferDecoder is the service name. This notice does not represent that an incorporated company exists or certify legal compliance.')
    year=datetime.now(timezone.utc).year
    for heading,body in LEGAL_SECTIONS: story += [p(heading,'legalhead'),p(body.replace('© 2026',f'© {year}'),'legal')]
    story += [card([p('OPERATOR INFORMATION','label'),p('The legal operator / rights-holder identity and a monitored legal contact have not been confirmed for this report. The service operator must complete these details and obtain appropriate legal review. Privacy information: offerdecoder.online/privacy.','legal')],'#FFF6E7'),Spacer(1,8),p('Reference framework: Indian Consumer Protection Act, 2019; U.S. Copyright Office guidance on notices and AI-generated material. These references do not certify compliance or replace legal advice.','legal')]
    links=[('Consumer Protection Act','https://www.indiacode.nic.in/bitstream/123456789/15256/5/A2019-35.pdf'),('Copyright notice guidance','https://www.copyright.gov/circs/circ03.pdf'),('AI copyright guidance','https://copyright.gov/newsnet/2025/1060.html')]
    story.append(p(' / '.join(f'<link href="{url}" color="{GREEN}">{label}</link>' for label,url in links),'legal',True))

    def header(canvas, document):
        canvas.saveState(); w,h=A4
        canvas.setFillColor(colors.HexColor(INK));canvas.setStrokeColor(colors.HexColor(GREEN));canvas.setLineWidth(1)
        canvas.roundRect(44,h-54,27,27,8,fill=1,stroke=1)
        canvas.setLineCap(1);canvas.setStrokeColor(colors.HexColor('#66827C'));canvas.setLineWidth(1.5)
        for yy,ww in [(9,12),(14,8),(19,4)]: canvas.line(51,h-27-yy,51+ww,h-27-yy)
        canvas.setStrokeColor(colors.HexColor('#37C797'));canvas.setLineWidth(2)
        path=canvas.beginPath();path.moveTo(58,h-45);path.lineTo(61,h-48);path.lineTo(66,h-42);canvas.drawPath(path)
        canvas.setFillColor(colors.HexColor(INK));canvas.setFont('ODBold',15);canvas.drawString(80,h-47,'OfferDecoder')
        canvas.setFillColor(colors.HexColor(MUTED));canvas.setFont('ODBody',7);canvas.drawRightString(w-44,h-43,'PRIVATE OFFER REPORT / '+('USA' if us else 'INDIA'))
        canvas.setStrokeColor(colors.HexColor(LINE));canvas.setLineWidth(.6);canvas.line(44,h-68,w-44,h-68)
        canvas.restoreState()
    out=BytesIO()
    doc=SimpleDocTemplate(out,pagesize=A4,leftMargin=44,rightMargin=44,topMargin=88,bottomMargin=62,title='OfferDecoder - Full offer report',author='OfferDecoder')
    doc.build(story,onFirstPage=header,onLaterPages=header,canvasmaker=ReportCanvas)
    return out.getvalue()
