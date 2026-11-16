import unittest
from unittest.mock import patch
from datetime import datetime,timezone
from scripts import collect_live as m

class PublicDataTests(unittest.TestCase):
 def test_null(self): self.assertIsNone(m.number(None))
 def test_empty(self): self.assertIsNone(m.number(''))
 def test_nan(self): self.assertIsNone(m.number('NaN'))
 def test_sentinel(self): self.assertIsNone(m.number(-9999))
 def test_negative_stage(self): self.assertEqual(m.number(-1.2),-1.2)
 def test_boolean(self): self.assertIsNone(m.number(True))
 def test_timezone(self): self.assertEqual(m.parse_time('2026-11-17T08:00:00',True).hour,0)
 def test_naive_disallowed(self): self.assertIsNone(m.parse_time('2026-11-17T08:00:00'))
 def test_invalid_date(self): self.assertIsNone(m.parse_time('bad'))
 def test_same_distance(self): self.assertEqual(m.distance(24,121,24,121),0)
 def test_url_guard(self):
  with self.assertRaises(ValueError):m.fetch_json('https://localhost/private')
 def test_no_secret(self):
  with patch.dict('os.environ',{'CWA_API_KEY':''}):self.assertEqual(m.cwa_rainfall()['status'],'requires_configuration')
 def test_exception_does_not_expose_url(self):
  def bad():raise ValueError('secret-token')
  self.assertNotIn('secret-token',str(m.envelope('s','https://x','k',1,bad)))
 def test_missing_water(self):
  with patch.object(m,'fetch_json',return_value=([{'stationid':'A','datetime':'2026-11-17T08:00:00','waterlevel':'-9999','checkresult':'true'}],m.iso(),False)):
   row=m.water_observations()['data'][0];self.assertIsNone(row['level_m']);self.assertEqual(row['quality'],'needs_review')
 def test_water_clock(self):
  with patch.object(m,'fetch_json',return_value=([{'stationid':'A','datetime':'2026-11-17T08:00:00','waterlevel':'0','checkresult':'true'}],m.iso(),False)):
   row=m.water_observations()['data'][0];self.assertEqual(row['observed_at'],'2026-11-17T00:00:00Z');self.assertEqual(row['level_m'],0)
 def test_empty_alert(self):
  with patch.object(m,'fetch_json',return_value=([],m.iso(),False)):
   x=m.slope_alerts();self.assertEqual(x['status'],'ok');self.assertEqual(x['data']['count'],0)
 def test_no_alert_placeholder(self):
  with patch.object(m,'fetch_json',return_value=([{'AlertType':'-','AlertLevel':'-','LandslideName':'目前無警戒'}],m.iso(),False)):
   self.assertEqual(m.slope_alerts()['data']['count'],0)
 def test_bad_alert_schema(self):
  with patch.object(m,'fetch_json',return_value=([{'text':'broken'}],m.iso(),False)):self.assertEqual(m.slope_alerts()['status'],'unavailable')
 def test_valid_alert(self):
  with patch.object(m,'fetch_json',return_value=([{'AlertType':'L','AlertLevel':'r','County':'花蓮縣'}],m.iso(),False)):
   self.assertEqual(m.slope_alerts()['data']['count'],1)
 def test_bad_weather(self):
  with patch.object(m,'fetch_json',return_value=({'error':True},m.iso(),False)):self.assertEqual(m.weather(m.REGIONS[0])['status'],'unavailable')
 def test_bad_satellite(self):
  with patch.object(m,'fetch_json',return_value=({},m.iso(),False)):self.assertEqual(m.satellite(m.REGIONS[0])['status'],'unavailable')
 def test_regions_not_asset(self):self.assertTrue(all(r['location_status']=='regional_reference_not_asset' for r in m.REGIONS))
if __name__=='__main__': unittest.main()
