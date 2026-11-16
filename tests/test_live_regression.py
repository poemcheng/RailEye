import unittest
from unittest.mock import patch
from scripts import collect_live as m
class RegressionTests(unittest.TestCase):
 def test_satellite_null_browse(self):
  d={'type':'FeatureCollection','features':[{'properties':{'sceneName':'TEST_ONLY','startTime':'2024-06-01T00:00:00Z','browse':None},'geometry':None}]}
  with patch.object(m,'fetch_json',return_value=(d,m.iso(),False)):
   x=m.satellite(m.REGIONS[0]);self.assertEqual(x['status'],'ok');self.assertIsNone(x['data']['scenes'][0]['browse_url'])
 def test_negative_rain_is_missing(self):self.assertIsNone(m.nonnegative(-99))
 def test_zero_rain_valid(self):self.assertEqual(m.nonnegative(0),0)
 def test_climate_period(self):
  d={'header':{'range':'2001-2025'},'properties':{'parameter':{}}}
  with patch.object(m,'fetch_json',return_value=(d,m.iso(),False)):self.assertEqual(m.climate(m.REGIONS[0])['data']['header']['start'],'2001-2025')
if __name__=='__main__':unittest.main()
