"""A downloadable snapshot of the purchased report. No model calls or remote assets."""
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether


def render_report(session, result, created_at):
    out = BytesIO()
    doc = SimpleDocTemplate(out, pagesize=(595.28, 841.89), rightMargin=44, leftMargin=44,
                            topMargin=48, bottomMargin=45, title="OfferDecode - Full offer report", author="OfferDecode")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Copy", fontName="Helvetica", fontSize=9, leading=14, spaceAfter=7, textColor=colors.HexColor("#334155")))
    styles.add(ParagraphStyle(name="Label", parent=styles["Copy"], fontSize=8, textColor=colors.HexColor("#64748b")))
    styles.add(ParagraphStyle(name="Amount", fontName="Helvetica-Bold", fontSize=30, leading=36, textColor=colors.HexColor("#047857"), spaceAfter=10))
    styles.add(ParagraphStyle(name="Right", parent=styles["Copy"], alignment=TA_RIGHT))
    styles["Heading1"].textColor = colors.HexColor("#0f172a")
    styles["Heading2"].textColor = colors.HexColor("#047857")
    styles["Heading2"].spaceBefore = 16
    styles["Heading2"].keepWithNext = True
    us = session.get("country") == "us"
    currency = "USD" if us else "INR"
    def text(value):
        return escape(str(value)).replace("\n", "<br/>")
    def p(value, style="Copy"):
        return Paragraph(text(value), styles[style])
    def money(value):
        return f"{currency} {float(value or 0):,.0f}"
    story = [p("OFFERDECODE / PURCHASED REPORT", "Label"), p("Your offer, decoded", "Heading1"),
             p(" / ".join(filter(None, [session.get("role"), session.get("company")])) or "Offer report"),
             p(f"{'United States' if us else 'India'} | Prepared {created_at.strftime('%d %b %Y')} | Amounts in {currency}", "Label"),
             Spacer(1, 10), p("Base salary take-home per month" if us else "Fixed in-hand per month", "Label"),
             p(money(result.get("monthlyFixed")), "Amount")]
    def table(rows):
        cells = [[p(label), p(value, "Right")] for label, value in rows]
        t = Table(cells, colWidths=[333, 174], hAlign="LEFT")
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                              ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f1f5f9"), colors.white]),
                              ("LINEBELOW", (0, 0), (-1, -1), .3, colors.HexColor("#e2e8f0"))]))
        story.append(KeepTogether([t]) if len(rows) <= 8 else t)
    table([("Headline annual compensation" if us else "Headline annual CTC", money(result.get("ctc"))),
           ("Fixed take-home per year", money(result.get("annualTakeHomeFixed"))),
           ("Yearly average per month if variable / equity pays in full", money(result.get("monthlyWithVariable"))),
           ("One-time joining / signing bonus after tax (estimate)", money(result.get("joiningAfterTax")))])
    story.append(p("Bonus and equity are not guaranteed monthly cash. This is an estimate, not tax, legal or financial advice."))
    derived = result.get("derived", {})
    labels = [("base", "Base salary"), ("bonus", "Target bonus (not guaranteed)"), ("rsus", "Annual RSUs / equity"),
              ("signing", "Signing bonus (one-time)"), ("k401", "Employee 401(k) saving")] if us else [
              ("basic", "Basic salary"), ("hra", "HRA"), ("specialAndOther", "Special / other allowances"),
              ("employerPF", "Employer PF"), ("gratuity", "Gratuity"), ("otherNonCash", "Other non-cash"),
              ("variable", "Variable pay (not guaranteed)"), ("joining", "Joining bonus (one-time)"), ("esops", "Annual ESOP value")]
    story.append(p("Compensation breakdown - annual amounts", "Heading2"))
    table([(label, money(derived[key])) for key, label in labels if derived.get(key)])
    story.append(p("Tax estimates", "Heading2"))
    story.append(p(result.get("meta", {}).get("regime", ""), "Label"))
    tax = result.get("taxFixed", {})
    tax_labels = [("taxable", "Federal taxable income"), ("federal", "Federal income tax"), ("stateTax", "State income tax"),
                  ("ss", "Social Security"), ("medicare", "Medicare"), ("totalTax", "Total annual taxes (including bonus / equity)")] if us else [
                  ("taxable", "Taxable income"), ("slabTax", "Income tax before rebate"), ("rebate", "Rebate / marginal relief"),
                  ("cess", "Health and education cess"), ("totalTax", "Total annual income tax on fixed pay")]
    table([(label, money(tax.get(key))) for key, label in tax_labels])
    if result.get("taxOnVariable"):
        story.append(p(f"Extra tax if variable pay / target bonus pays in full: {money(result['taxOnVariable'])}"))
    if us:
        base_tax = result.get("taxBase", {})
        story.append(p("Base salary take-home calculation", "Heading2"))
        table([("Annual base salary", money(derived.get("base"))), ("Employee 401(k)", money(base_tax.get("k401"))),
               ("Federal tax", money(base_tax.get("federal"))), ("State tax", money(base_tax.get("stateTax"))),
               ("Social Security", money(base_tax.get("ss"))), ("Medicare", money(base_tax.get("medicare"))),
               ("Annual base take-home", money(result.get("annualTakeHomeFixed")))])
    else:
        story.append(p("Fixed take-home calculation", "Heading2"))
        table([("Fixed CTC", money(result.get("fixedCTC"))), ("Fixed gross cash salary", money(result.get("cashGross"))),
               ("Employee PF", money(derived.get("employeePF"))), ("Professional tax", money(derived.get("profTax"))),
               ("Income tax", money(tax.get("totalTax"))), ("Annual fixed take-home", money(result.get("annualTakeHomeFixed")))])
    story.append(p("Assumptions and limitations", "Heading2"))
    seen = set()
    for value in result.get("assumptions", []):
        story.append(p("- " + value))
        seen.add(value)
    for value in (result.get("stateNote"), result.get("meta", {}).get("countryNote")):
        if value and value not in seen:
            story.append(p(value))
            seen.add(value)
    story.append(p("Calculations use the saved offer inputs. Missing components may be estimated. Check the figures against your original offer and confirm tax treatment with a qualified adviser."))
    story.append(p("Offer flags and questions to ask", "Heading2"))
    for flag in result.get("flags", []):
        block = [p(f"{flag.get('level', 'info').upper()}: {flag.get('text', '')}")]
        for key, label in (("letter", "From your letter"), ("why", "Why it matters"), ("ask", "Ask your employer")):
            if flag.get(key):
                block.append(p(f"{label}: {flag[key]}"))
        story.extend(block)
        story.append(Spacer(1, 5))
    story.append(p("Negotiation tips", "Heading2"))
    story.extend(p(f"{i}. {value}") for i, value in enumerate(result.get("tips", []), 1))
    story.append(p("Keep this PDF for your records. Online reports and share links expire after 90 days. Verify all extracted details against your original offer letter.", "Label"))
    def footer(canvas, document):
        canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
        canvas.line(44, 34, 551, 34)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(44, 22, "offerdecoder.online | Private offer report")
        canvas.drawRightString(551, 22, f"Page {document.page}")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
