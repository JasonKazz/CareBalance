import base64
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from backend.documents.extract import extract, document_pages
from backend.repricing import reprice, parse_activity, amount
from tests import test_calculator
ROOT=Path(__file__).resolve().parents[1]
CSV=(ROOT/'data/synthetic/sample-activity.csv').read_text()
TEXT=(ROOT/'data/synthetic/sample-offer.txt').read_text()
def doc(text=TEXT):return {'name':'offer.txt','content':base64.b64encode(text.encode()).decode(),'mode':'local'}
def pdf_bytes():
    writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 50 730 Td (FICTIONAL TEST CONTRACT) Tj 0 -24 Td (VISIT-A | Short clinic appointment | $110.00) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream);output=io.BytesIO();writer.write(output);return output.getvalue()
class RepricingTests(unittest.TestCase):
    def test_known_totals_and_unmatched_exclusion(self):
        result=reprice({'activity_csv':CSV,'rates':extract(doc())['rates'],'confirmed':True})
        self.assertEqual(result['summary']['current_matched'],613500)
        self.assertEqual(result['summary']['proposed_matched'],587800)
        self.assertEqual(result['summary']['annual_delta'],-25700)
        self.assertEqual(result['summary']['all_current'],631500)
        self.assertEqual(result['unmatched'][0]['code'],'OTHER-G')
        self.assertAlmostEqual(result['summary']['volume_coverage_pct'],5300/5500*100)
        self.assertEqual(sum(r['annual_delta'] for r in result['matched']),-25700)
    def test_decimal_cents(self):
        r=reprice({'activity_csv':'code,description,annual_volume,current_rate\nA,x,3,0.10\n','rates':[{'code':'A','rate':'0.20'}],'confirmed':True})
        self.assertEqual(r['summary']['annual_delta'],.30)
    def test_counteroffer_rounds_half_cents_in_decimal(self):
        r=reprice({'activity_csv':'code,description,annual_volume,current_rate\nA,x,1,38.10\n','rates':[{'code':'A','rate':'38.10'}],'confirmed':True,'uplift_pct':5})
        self.assertEqual(r['matched'][0]['proposed_rate'],40.01)
    def test_zero_rate_is_not_missing(self):
        r=reprice({'activity_csv':'code,description,annual_volume,current_rate\nA,x,3,0.10\n','rates':[{'code':'A','rate':0}],'confirmed':True})
        self.assertEqual(r['summary']['proposed_matched'],0)
        self.assertIsNone(r['summary']['uniform_uplift_to_break_even_pct'])
    def test_duplicate_and_unconfirmed_rates_rejected(self):
        for payload in [dict(activity_csv=CSV,rates=[{'code':'VISIT-A','rate':100}],confirmed=False),dict(activity_csv=CSV,rates=[{'code':'VISIT-A','rate':100}]*2,confirmed=True)]:
            with self.assertRaises(ValueError):reprice(payload)
    def test_no_positive_matches_rejected(self):
        with self.assertRaises(ValueError):reprice({'activity_csv':CSV,'rates':[{'code':'UNKNOWN','rate':100}],'confirmed':True})
    def test_csv_validation(self):
        for text in ['', 'code,patient_name,annual_volume,current_rate\nA,Someone,1,10', 'code,description,annual_volume,current_rate\nA,x,-1,10', 'code,description,annual_volume,current_rate\nA,x,1,10\nA,x,2,10', 'code,description,annual_volume,current_rate\nA,x,2,1.001', 'code,description,annual_volume,current_rate\nA,x,2,NaN']:
            with self.subTest(text=text),self.assertRaises(ValueError):parse_activity(text)
    def test_source_evidence(self):
        result=extract(doc());self.assertEqual(len(result['rates']),6)
        self.assertTrue(all(r['source_supported'] for r in result['rates']))
    def test_conflicting_rates_are_flagged(self):
        rates=extract(doc('A | first | $10.00\nA | second | $20.00'))['rates']
        self.assertTrue(all(r['ambiguous'] for r in rates))
    def test_percentage_not_parsed_as_dollars(self):
        self.assertEqual(extract(doc('A | service | 120% of Medicare'))['rates'],[])
    def test_hallucinated_quote_not_supported(self):
        fake={'rates':[{'code':'A','description':'x','rate':'10.00','page':1,'quote':'A $10.00 invented'}],'limitations':[]}
        with patch('backend.documents.extract.extract_rates',return_value=(fake,None)):
            self.assertFalse(extract(dict(doc('A $10.00 genuine'),mode='gemini',consent=True))['rates'][0]['source_supported'])
    def test_gemini_requires_explicit_consent(self):
        with self.assertRaises(ValueError):extract(dict(doc(),mode='gemini',consent=False))
    def test_actual_pdf_text_extraction(self):
        result=extract({'name':'offer.pdf','content':base64.b64encode(pdf_bytes()).decode(),'mode':'local'})
        self.assertEqual(result['rates'][0]['code'],'VISIT-A')
        self.assertTrue(result['rates'][0]['source_supported'])
    def test_invalid_documents(self):
        for payload in [{'name':'x.exe','content':'YQ=='},{'name':'x.pdf','content':'YQ=='},{'name':'x.txt','content':'%%%'}]:
            with self.assertRaises(ValueError):document_pages(payload)
    def test_api_extract_and_compare(self):
        # Use the same real ephemeral HTTP server helper as existing API tests.
        test_calculator.APITests.setUpClass()
        try:
            helper=test_calculator.APITests();status,raw=helper.request('/api/extract',json.dumps(doc()).encode())
            self.assertEqual(status,200)
            rates=json.loads(raw)['rates']
            status,raw=helper.request('/api/reprice',json.dumps({'activity_csv':CSV,'rates':rates,'confirmed':True}).encode())
            self.assertEqual(status,200);self.assertEqual(json.loads(raw)['summary']['annual_delta'],-25700)
        finally:test_calculator.APITests.tearDownClass()
