import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('soil',Path(__file__).resolve().parents[1]/'scripts/collect_soil.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class SoilTests(unittest.TestCase):
 def setUp(self):
  self.r=s.REGIONS[0];self.t='2026-11-10T00:00:00Z'
  self.d={'latitude':24.2,'longitude':121.7,'hourly':{'time':[1793836800]},'hourly_units':{}}
  for v in s.VARS:self.d['hourly'][v]=[.3];self.d['hourly_units'][v]='m³/m³'
 def norm(self,d=None):return s.normalize_openmeteo(d or self.d,self.r,self.t)
 def test_three_real_layers(self):self.assertEqual(self.norm()['rows'][0]['values']['s2'],.3)
 def test_fourth_never_remapped(self):self.assertIsNone(self.norm()['rows'][0]['values']['s4'])
 def test_publication_unknown(self):self.assertIsNone(self.norm()['rows'][0]['available_at'])
 def test_first_seen(self):self.assertEqual(self.norm()['rows'][0]['first_seen_at'],self.t)
 def test_first_seen_preserved(self):
  a=self.norm();b=s.normalize_openmeteo(self.d,self.r,'2026-11-11T00:00:00Z',a);self.assertEqual(a['rows'][0]['first_seen_at'],b['rows'][0]['first_seen_at'])
 def test_revision_changes_first_seen(self):
  a=self.norm();self.d['hourly'][s.VARS[1]]=[.31];b=s.normalize_openmeteo(self.d,self.r,'2026-11-11T00:00:00Z',a);self.assertNotEqual(a['rows'][0]['value_hash'],b['rows'][0]['value_hash']);self.assertEqual(b['rows'][0]['first_seen_at'],'2026-11-11T00:00:00Z')
 def test_different_grid_no_first_seen_reuse(self):
  a=self.norm();self.d['longitude']=121.8;b=s.normalize_openmeteo(self.d,self.r,'2026-11-11T00:00:00Z',a);self.assertEqual(b['rows'][0]['first_seen_at'],'2026-11-11T00:00:00Z')
 def test_null_not_zero(self):self.d['hourly'][s.VARS[1]]=[None];self.assertIsNone(self.norm()['rows'][0]['values']['s2'])
 def test_negative_not_moisture(self):self.assertIsNone(s.moisture(-999))
 def test_boolean_rejected(self):self.assertIsNone(s.moisture(True))
 def test_nan_rejected(self):self.assertIsNone(s.moisture(float('nan')))
 def test_unit_mismatch(self):
  self.d['hourly_units'][s.VARS[0]]='%'
  with self.assertRaises(ValueError):self.norm()
 def test_length_mismatch(self):
  self.d['hourly'][s.VARS[0]]=[]
  with self.assertRaises(ValueError):self.norm()
 def test_duplicate_times(self):
  self.d['hourly']['time']*=2
  for v in s.VARS:self.d['hourly'][v]*=2
  with self.assertRaises(ValueError):self.norm()
 def test_future_soil(self):
  self.d['hourly']['time']=[1893836800]
  with self.assertRaises(ValueError):self.norm()
 def test_outside_grid(self):
  self.d['latitude']=50
  with self.assertRaises(ValueError):self.norm()
 def test_naive_time_rejected(self):
  with self.assertRaises(ValueError):s.stamp('2026-11-01')
 def test_invalid_cds_import(self):
  with self.assertRaises(ValueError):s.validate_cds({'product':'reanalysis-era5-land','unit':'percent','depths_cm':s.DEPTHS})
 def test_cds_depth_exact(self):
  d=self.norm();d.update(product='reanalysis-era5-land',direct_cds=True);d['depths_cm']=[[0,7],[7,28],[28,100],[100,255]]
  with self.assertRaises(ValueError):s.validate_cds(d)
if __name__=='__main__':unittest.main()
