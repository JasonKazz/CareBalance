import copy
import json
import random
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from backend.models.contracts import evaluate
from backend.simulation.engine import analyze, validate
from backend.server import Handler

EXAMPLE = json.loads((Path(__file__).resolve().parents[1] / "data/synthetic/community-clinic.json").read_text())

class CalculatorTests(unittest.TestCase):
    def test_hand_calculated_monthly_accounting(self):
        result = analyze(EXAMPLE)
        baseline, stress = result["baseline"], result["stress"]
        self.assertEqual(baseline["visits"], 450)
        self.assertEqual(stress["visits"], 630)
        self.assertEqual(baseline["contracts"]["ffs"]["cost"], 50750)
        self.assertEqual(baseline["contracts"]["ffs"]["revenue"], 49500)
        self.assertEqual(baseline["contracts"]["ffs"]["surplus"], -1250)
        self.assertEqual(stress["contracts"]["pmpm"]["surplus"], -50)
        self.assertAlmostEqual(baseline["contracts"]["pmpm"]["margin_pct"], 6250/57000*100)

    def test_known_feasible_interval_and_conflicting_constraints(self):
        terms=analyze(EXAMPLE)["terms"]
        self.assertEqual(terms["pmpm"]["minimum_rate"], 40.04)
        self.assertEqual(terms["pmpm"]["maximum_rate"], 43.33)
        self.assertTrue(terms["pmpm"]["feasible"])
        self.assertFalse(terms["ffs"]["feasible"])
        self.assertEqual(terms["ffs"]["minimum_rate"], 118.72)
        self.assertEqual(terms["ffs"]["maximum_rate"], 103.17)

    def test_capacity_is_independent_of_payment(self):
        result=analyze(dict(EXAMPLE, stress_pct=70, payer_budget=10000000, pmpm_rate=500))
        self.assertEqual(result["stress"]["visits"], 765)
        self.assertEqual(result["stress"]["capacity_gap"], 115)
        for terms in result["terms"].values(): self.assertFalse(terms["feasible"])
        self.assertEqual(result["stress"]["contracts"]["ffs"]["cost"], 61775)

    def test_low_budget_has_no_solution(self):
        for terms in analyze(dict(EXAMPLE,payer_budget=45000))["terms"].values():
            self.assertFalse(terms["feasible"])
            self.assertIsNone(terms["recommended_rate"])

    def test_zero_revenue_and_zero_cost_are_finite_json(self):
        result=analyze(dict(EXAMPLE,ffs_rate=0,pmpm_rate=0,fixed_cost=0,visit_cost=0,payer_budget=0,min_margin=0))
        self.assertIsNone(result["baseline"]["contracts"]["ffs"]["margin_pct"])
        self.assertTrue(result["terms"]["ffs"]["feasible"])
        json.dumps(result,allow_nan=False)

    def test_invalid_inputs(self):
        for key,value in [('patients',True),('patients',0),('patients',1.5),('fixed_cost',-1),('visit_cost',float('nan')),('pmpm_rate',float('inf')),('stress_pct',201),('min_margin','5')]:
            with self.subTest(key=key,value=value), self.assertRaises(ValueError):
                validate(dict(EXAMPLE,**{key:value}))
        for data in [[],{},dict(EXAMPLE,unknown=3)]:
            with self.assertRaises(ValueError): validate(data)

    def test_feasible_rates_actually_satisfy_both_scenarios(self):
        rng=random.Random(19)
        for _ in range(100):
            inputs=dict(EXAMPLE, payer_budget=rng.uniform(60000,150000),capacity=2000,
                        fixed_cost=rng.uniform(10000,50000),visit_cost=rng.uniform(5,70),stress_pct=rng.uniform(0,100))
            result=analyze(inputs)
            for model,rate_key in [('ffs','ffs_rate'),('pmpm','pmpm_rate')]:
                terms=result['terms'][model]
                if not terms['feasible']: continue
                for rate in [terms['minimum_rate'],terms['maximum_rate']]:
                    changed=dict(inputs,**{rate_key:rate})
                    for case in ['baseline','stress']:
                        self.assertTrue(evaluate(changed,result[case]['visits'])['contracts'][model]['feasible'])
                below=dict(inputs,**{rate_key:terms['minimum_rate']-.01})
                self.assertTrue(any(not evaluate(below,result[c]['visits'])['contracts'][model]['margin_ok'] for c in ['baseline','stress']))

    def test_deterministic_and_does_not_mutate(self):
        original=copy.deepcopy(EXAMPLE)
        self.assertEqual(analyze(EXAMPLE),analyze(EXAMPLE))
        self.assertEqual(EXAMPLE,original)

class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,path,data=None,kind='application/json'):
        req=urllib.request.Request(self.base+path,data=data,headers={'Content-Type':kind})
        try:
            with urllib.request.urlopen(req,timeout=5) as response: return response.status,response.read()
        except urllib.error.HTTPError as e: return e.code,e.read()
    def test_real_api_response(self):
        status,body=self.request('/api/analyze',json.dumps(EXAMPLE).encode())
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['terms']['pmpm']['minimum_rate'],40.04)
    def test_bad_requests(self):
        for data,kind,expected in [(b'{','application/json',400),(b'{}','application/json',400),(b'{}','text/plain',415),(b' '*16385,'application/json',413)]:
            self.assertEqual(self.request('/api/analyze',data,kind)[0],expected)
    def test_static_allowlist_and_api(self):
        for path in ['/', '/styles.css','/app.js','/api/schema','/api/example','/api/health']:
            self.assertEqual(self.request(path)[0],200)
        for path in ['/.env','/backend/server.py','/../.env']:
            self.assertEqual(self.request(path)[0],404)

if __name__ == '__main__': unittest.main()
