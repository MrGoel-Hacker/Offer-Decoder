"""US state individual income tax data, tax year 2026, single filer.

Source: Tax Foundation, "State Individual Income Tax Rates and Brackets, 2026"
(data as of February 11, 2026): https://taxfoundation.org/data/all/state/state-income-tax-rates-2026/

Verified at owning state agencies on 2026-10-23: CA (ftb.ca.gov - latest published
schedule is TY2025; 2026 instructions reuse it), NY (tax.ny.gov NYS-50-T-NYS 1/26 - official
revised 2026 schedule incl. benefit recapture rows; above $1,077,550 taxable the latest published
filing top rates are used as an approximation), NJ (nj.gov/treasury/taxation),
MA (mass.gov - TY2026 surtax threshold $1,107,750), IL (tax.illinois.gov - 2026 exemption $2,925),
TX (comptroller.texas.gov - no individual income tax), WA (dor.wa.gov - no wage income tax;
a 9.9% tax over $1M AGI starts 2028). All other states use the Tax Foundation table and are
NOT source-verified.

Simplifications (labelled as estimates in the UI):
- Standard deduction and deduction-type personal exemptions applied where listed;
  exemptions structured as tax CREDITS (AR, AZ, DE, NE, OR, UT and dependent credits) are ignored
  (small overestimate of tax).
- Phaseouts (CT, MD, WI, RI, ME, OH...) and local/city income taxes are not modelled.
- Washington taxes capital gains only -> treated as no wage tax.
- brackets: list of (threshold, rate) - rate applies to taxable income above the threshold.
"""

NO_TAX = {"AK", "FL", "NV", "NH", "SD", "TN", "TX", "WA", "WY"}

STATES = {
    "AL": {"name": "Alabama", "std": 3000, "exempt": 1500, "brackets": [(0, .02), (500, .04), (3000, .05)]},
    "AK": {"name": "Alaska", "none": True},
    "AZ": {"name": "Arizona", "std": 8350, "brackets": [(0, .025)]},
    "AR": {"name": "Arkansas", "std": 2470, "brackets": [(0, .02), (4600, .039)]},
    "CA": {"name": "California", "std": 5706, "note": "CA has not published its 2026 schedule - using CA's 2025 brackets with the deduction from CA's 2026 estimated-tax instructions (ftb.ca.gov). CA SDI (about 1.3% of wages, no cap) is not included.", "brackets": [(0, .01), (11079, .02), (26264, .04), (41452, .06), (57542, .08), (72724, .093), (371479, .103), (445771, .113), (742953, .123), (1000000, .133)]},
    "CO": {"name": "Colorado", "std": 16100, "brackets": [(0, .044)]},
    "CT": {"name": "Connecticut", "exempt": 15000, "brackets": [(0, .02), (10000, .045), (50000, .055), (100000, .06), (200000, .065), (250000, .069), (500000, .0699)]},
    "DE": {"name": "Delaware", "std": 3250, "brackets": [(2000, .022), (5000, .039), (10000, .048), (20000, .052), (25000, .0555), (60000, .066)]},
    "DC": {"name": "Washington DC", "std": 16100, "brackets": [(0, .04), (10000, .06), (40000, .065), (60000, .085), (250000, .0925), (500000, .0975), (1000000, .1075)]},
    "FL": {"name": "Florida", "none": True},
    "GA": {"name": "Georgia", "std": 12000, "brackets": [(0, .0519)]},
    "HI": {"name": "Hawaii", "std": 4400, "exempt": 1144, "brackets": [(0, .014), (9600, .032), (14400, .055), (19200, .064), (24000, .068), (36000, .072), (48000, .076), (125000, .079), (175000, .0825), (225000, .09), (275000, .10), (325000, .11)]},
    "ID": {"name": "Idaho", "std": 16100, "brackets": [(4811, .053)]},
    "IL": {"name": "Illinois", "exempt": 2925, "brackets": [(0, .0495)]},
    "IN": {"name": "Indiana", "exempt": 1000, "brackets": [(0, .0295)]},
    "IA": {"name": "Iowa", "std": 16100, "brackets": [(0, .038)]},
    "KS": {"name": "Kansas", "std": 3605, "exempt": 9160, "brackets": [(0, .052), (23000, .0558)]},
    "KY": {"name": "Kentucky", "std": 3360, "brackets": [(0, .035)]},
    "LA": {"name": "Louisiana", "std": 12875, "brackets": [(0, .03)]},
    "ME": {"name": "Maine", "std": 8350, "exempt": 5300, "brackets": [(0, .058), (27399, .0675), (64849, .0715)]},
    "MD": {"name": "Maryland", "std": 3350, "exempt": 3200, "brackets": [(0, .02), (1000, .03), (2000, .04), (3000, .0475), (100000, .05), (125000, .0525), (150000, .055), (250000, .0575), (500000, .0625), (1000000, .065)]},
    "MA": {"name": "Massachusetts", "exempt": 4400, "note": "MA PFML payroll contributions are not included.", "brackets": [(0, .05), (1107750, .09)]},
    "MI": {"name": "Michigan", "exempt": 5900, "brackets": [(0, .0425)]},
    "MN": {"name": "Minnesota", "std": 15300, "brackets": [(0, .0535), (33310, .068), (109430, .0785), (203150, .0985)]},
    "MS": {"name": "Mississippi", "std": 2300, "exempt": 6000, "brackets": [(10000, .04)]},
    "MO": {"name": "Missouri", "std": 16100, "brackets": [(1348, .02), (2696, .025), (4044, .03), (5392, .035), (6740, .04), (8088, .045), (9436, .047)]},
    "MT": {"name": "Montana", "std": 16100, "brackets": [(0, .047), (47500, .0565)]},
    "NE": {"name": "Nebraska", "std": 8850, "brackets": [(0, .0246), (4130, .0351), (24760, .0455)]},
    "NV": {"name": "Nevada", "none": True},
    "NH": {"name": "New Hampshire", "none": True},
    "NJ": {"name": "New Jersey", "exempt": 1000, "note": "NJ employee payroll contributions (unemployment/disability/family leave) are not included.", "brackets": [(0, .014), (20000, .0175), (35000, .035), (40000, .05525), (75000, .0637), (500000, .0897), (1000000, .1075)]},
    "NM": {"name": "New Mexico", "std": 16100, "brackets": [(0, .015), (5500, .032), (16500, .043), (33500, .047), (66500, .049), (210000, .059)]},
    "NY": {"name": "New York", "std": 8000, "note": "NY estimate uses NY's official 2026 withholding schedule incl. the high-income benefit recapture (tax.ny.gov NYS-50-T-NYS, effective Jan 1, 2026); the 2026 filing-year computation is not yet published, so filed tax can differ slightly. NY paid family leave is not included.", "brackets": [(0, .039), (8500, .044), (11700, .0515), (13900, .054), (80650, .059), (96800, .0703), (107650, .0753), (157650, .064), (215400, .1144), (265400, .0735), (1077550, .0965), (5000000, .103), (25000000, .109)]},
    "NC": {"name": "North Carolina", "std": 12750, "brackets": [(0, .0399)]},
    "ND": {"name": "North Dakota", "std": 16100, "brackets": [(48475, .0195), (244825, .025)]},
    "OH": {"name": "Ohio", "exempt": 2400, "brackets": [(26050, .0275)]},
    "OK": {"name": "Oklahoma", "std": 6350, "exempt": 1000, "brackets": [(3750, .025), (4900, .035), (7200, .045)]},
    "OR": {"name": "Oregon", "std": 2910, "brackets": [(0, .0475), (4550, .0675), (11400, .0875), (125000, .099)]},
    "PA": {"name": "Pennsylvania", "brackets": [(0, .0307)]},
    "RI": {"name": "Rhode Island", "std": 11200, "exempt": 5250, "brackets": [(0, .0375), (82050, .0475), (186450, .0599)]},
    "SC": {"name": "South Carolina", "std": 8350, "brackets": [(0, 0), (3640, .03), (18230, .06)]},
    "SD": {"name": "South Dakota", "none": True},
    "TN": {"name": "Tennessee", "none": True},
    "TX": {"name": "Texas", "none": True},
    "UT": {"name": "Utah", "brackets": [(0, .045)]},
    "VT": {"name": "Vermont", "std": 7650, "exempt": 5300, "brackets": [(0, .0335), (49400, .066), (119700, .076), (249700, .0875)]},
    "VA": {"name": "Virginia", "std": 8750, "exempt": 930, "brackets": [(0, .02), (3000, .03), (5000, .05), (17000, .0575)]},
    "WA": {"name": "Washington", "none": True},
    "WV": {"name": "West Virginia", "exempt": 2000, "brackets": [(0, .0222), (10000, .0296), (25000, .0333), (40000, .0444), (60000, .0482)]},
    "WI": {"name": "Wisconsin", "std": 13960, "exempt": 700, "brackets": [(0, .035), (15110, .044), (51950, .053), (332720, .0765)]},
    "WY": {"name": "Wyoming", "none": True},
}
