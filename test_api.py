import unittest
from app import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def post(self, **values):
        return self.client.post('/api/v1/quotes', json={
            'plan': 'visit-60', 'region': 'tokyo', **values})

    def test_catalog(self):
        result = self.client.get('/api/v1/prices')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['plans']['visit-90']['price'], 16000)
        self.assertIsNone(result.json['photography']['face']['price'])

    def test_all_base_plans(self):
        for plan, expected in [('visit-60', 14000), ('visit-90', 17000),
                               ('visit-120', 20000), ('stay', 30000), ('charter', 56000)]:
            with self.subTest(plan=plan):
                self.assertEqual(self.post(plan=plan).json['total'], expected)

    def test_discount_excludes_extras(self):
        result = self.post(discounts=['repeater', 'younger', 'top'],
                           extension_units=1, options=['hard-m'], region='nearby')
        self.assertEqual(result.json['total'], 17800)

    def test_charter_formula(self):
        self.assertEqual(self.post(plan='charter', days=3).json['total'], 121000)
        self.assertEqual(self.post(plan='charter', days=2).json['total'], 81000)

    def test_remote_rounding_and_no_local_fare(self):
        result = self.post(region='remote', round_trip_fare=6000, round_trip_minutes=61).json
        self.assertEqual(result['prepaid_amount'], 7017)
        self.assertEqual(result['total'], 20017)

    def test_shooting_only(self):
        result = self.post(plan='visit-120', photography='body', shooting_only=True,
                           discounts=['repeater']).json
        self.assertEqual(result['total'], 12550)

    def test_consultation(self):
        for values in [dict(photography='face'), dict(photography='commercial'),
                       dict(plan='visit-120', extension_units=1, photography='body')]:
            result = self.post(**values).json
            self.assertIsNone(result['total'])
            self.assertEqual(result['status'], 'requires_consultation')
            self.assertTrue(result['unresolved'])

    def test_date_window(self):
        for start in ['14:00', '20:00']:
            self.assertEqual(self.post(plan='date', discounts=['repeater'], start_time=start).json['total'], 5000)
        for start in ['13:59', '20:01', '24:00']:
            self.assertEqual(self.post(plan='date', discounts=['repeater'], start_time=start).status_code, 400)

    def test_validation(self):
        cases = [dict(plan='unknown'), dict(plan=[]), dict(region={}),
                 dict(extension_units=True), dict(extension_units=-1), dict(days=3),
                 dict(discounts=['repeater', 'repeater']), dict(options=['missing']),
                 dict(shooting_only='true'), dict(shooting_only=True),
                 dict(region='remote'), dict(round_trip_fare=0),
                 dict(plan='date'), dict(typo=1), dict(plan='stay', extension_units=1)]
        for values in cases:
            with self.subTest(values=values):
                self.assertEqual(self.post(**values).status_code, 400)

    def test_http_errors(self):
        for value in [None, [], 'text', 1]:
            import json
            self.assertEqual(self.client.post('/api/v1/quotes', data=json.dumps(value),
                                             content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/api/v1/quotes', data='{', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/api/v1/quotes', data='x').status_code, 415)
        self.assertEqual(self.client.get('/missing').status_code, 404)
        self.assertEqual(self.client.get('/api/v1/quotes').status_code, 405)
        self.assertEqual(self.client.post('/api/v1/quotes', data='x' * 17000,
                                         content_type='application/json').status_code, 413)


if __name__ == '__main__':
    unittest.main()
