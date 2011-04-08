import unittest
from django.test.client import Client
from django.utils import simplejson as json
from tsudat.models import *

VALID_HAZARD_POINT = 2037

class TsudatTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_return_period(self):
        c = Client()

        # This is almost certainly overkill.
        # Its here temporarily for discussion purposes

        # Test the endpoint with no arguments
        rp = c.get('/tsudat/return_period/')
        self.assertEqual(rp.status_code, 400)
        assert "Wave Height must be specified" in rp.content

        # Test the endpoint with only the wave height argument 
        rp = c.get('/tsudat/return_period/?wh=1.0')
        self.assertEqual(rp.status_code, 400)
        assert "Wave Height Delta must be specified" in rp.content

        # Test the endpoint with the wave height and wave height delta argument 
        rp = c.get('/tsudat/return_period/?wh=1.0&whd=1.0')
        self.assertEqual(rp.status_code, 400)
        assert "Hazard Point must be specified" in rp.content

        # Test the endpoint with non-numeric wave height and wave height delta values 
        rp = c.get('/tsudat/return_period/?wh=abc&whd=1.0&hp=%d' % VALID_HAZARD_POINT)
        self.assertEqual(rp.status_code, 400)
        assert "Invalid" in rp.content
        
        rp = c.get('/tsudat/return_period/?wh=1.0&whd=abc&hp=%d' % VALID_HAZARD_POINT)
        self.assertEqual(rp.status_code, 400)
        assert "Invalid" in rp.content

        # Test the endpoint with an Invalid Hazard Point ID
        rp = c.get('/tsudat/return_period/?wh=1.0&whd=1.0&hp=1')
        self.assertEqual(rp.status_code, 404)
        assert "Invalid" in rp.content

        # END Overkill

        # Test the endpoint with a Valid Set of Values
        # Probably need a few more tests like this one to be sure the
        # appropriate values are returned in various situations
        rp = c.get('/tsudat/return_period/?wh=1.0&whd=1.0&hp=%d' % VALID_HAZARD_POINT)
        self.assertEqual(rp.status_code, 200)
        data = json.loads(rp.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(int(data[0]['fields']['return_period']), 1500)

    def test_return_periods(self):
        c = Client()
        rp = c.get('/tsudat/return_periods/')
        self.assertEqual(rp.status_code, 200)
        self.assertEqual(rp['Content-Type'], 'application/json')
        data = json.loads(rp.content)
        msg = ('The api should return a list of return periods'
                'The length of the list should be 22')
        assert len(data) == 22

    def test_hazard_points(self):
        pass

    def test_source_zones(self):
        pass

    def test_source_zone(self):
        pass

    def test_sub_faults(self):
        pass

    def test_events(self):
        pass

    def test_wave_height(self):
        pass

    def test_project(self):
        # Test POST/PUT
        # - Test invalid json post-data
        # - Test invalid geojson
        # - Test invalid geometry
        # - Test Incomplete/Invalid Project
        #   - Name Required
        #   - Max Area Required
        #   - Max Area Numeric
        # Test GET Single
        # Test Get Multiple
        # Test Delete
        pass

    def test_internal_polygon_types(self):
        pass

    def test_internal_polygon(self):
        pass

    def test_gauge_point(self):
        pass

    def test_scenario(self):
        pass

    def test_data_set(self):
        pass

    def test_project_data_set(self):
        pass

    def test_layer(self):
        pass

    def test_run_scenario(self):
        pass
