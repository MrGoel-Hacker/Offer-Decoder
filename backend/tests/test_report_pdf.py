"""Production report invariants: saved values, safe text and complete multi-page output."""
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
import sys
import pytest
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from report_pdf import render_report, money
from decoder import decode
from us_decoder import decode_us


@pytest.mark.parametrize('country', ['in', 'us'])
def test_full_report_keeps_saved_values_and_legal_footers(country):
    inp = {'baseSalary':145000,'targetBonus':14500,'rsuPerYear':25000,'state':'NY'} if country=='us' else {'ctc':1800000,'joiningBonus':100000,'variablePay':180000}
    result = (decode_us if country=='us' else decode)(inp)
    result['country'] = country
    session = {'country':country,'company':'Acme <Research> & Partners','role':'Engineer','input':inp}
    result['monthlyFixed'] = 12345  # Export the purchased snapshot, never recompute.
    before = deepcopy((session,result))
    pdf = PdfReader(BytesIO(render_report(session,result,datetime.now(timezone.utc))))
    texts = [page.extract_text() for page in pdf.pages]
    text = '\n'.join(texts)
    assert len(pdf.pages) >= 5
    assert 'Acme <Research> & Partners' in text
    assert money(12345,country=='us') in texts[0]
    for heading in ['Your offer, at a glance.','What becomes spendable cash?','The terms worth clarifying.','Your next conversation.','Legal notices and permitted use.']:
        assert heading in text
    for i, page in enumerate(texts,1):
        assert 'All rights reserved in protectable material' in page
        assert f'{i} / {len(pdf.pages)}' in page
    assert 'mandatory rights' in text.lower()
    assert 'OPERATOR INFORMATION' in text
    assert 'not been confirmed' in text
    assert 'FICTIONAL SAMPLE' not in text
    assert 'Offer p.2' not in text
    assert (session,result) == before
    assert 'Acme' not in str(pdf.metadata)
    assert any(page.get('/Annots') for page in pdf.pages)


def test_long_clause_content_is_not_dropped_or_clipped_to_a_fixed_page_count():
    inp={'ctc':1800000}
    result=decode(inp)
    result['flags']=[{'source':'clause','level':'warn','text':f'Notice condition {i}: '+('Review this condition in the agreement. '*12),'letter':('Captured summary, not a verified quotation. '*18)} for i in range(12)]
    pdf=PdfReader(BytesIO(render_report({'country':'in','input':inp},result,datetime.now(timezone.utc))))
    text='\n'.join(page.extract_text() for page in pdf.pages)
    assert len(pdf.pages) > 5
    for i in range(12): assert f'Notice condition {i}:' in text
    assert 'Legal notices and permitted use.' in text
    assert all('All rights reserved' in page.extract_text() for page in pdf.pages)


def test_minimal_legacy_snapshot_and_long_unbroken_input_still_export():
    session={'country':'in','company':'X'*400,'input':{'ctc':1800000}}
    pdf=PdfReader(BytesIO(render_report(session,{'ctc':1800000},datetime.now(timezone.utc))))
    text='\n'.join(page.extract_text() for page in pdf.pages)
    assert 'No flags captured' in text
    assert 'Legal notices and permitted use.' in text
    assert 'No breakdown captured' in text
