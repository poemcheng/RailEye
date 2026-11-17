"""Package the existing dashboard with its additive hydro module; do not rewrite old views."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1];site=root if '--in-place' in sys.argv else root/'_site'
p=site/'index.html';html=p.read_text(encoding='utf-8')
if 'hydro-ui.js?v=0.5.0' not in html:
 html=html.replace('</head>','<link rel="stylesheet" href="hydro.css?v=0.5.0"><script defer src="hydro-core.js?v=0.5.0"></script><script defer src="hydro-ui.js?v=0.5.0"></script>\n</head>')
html=html.replace('RailEye v0.4 · Public environmental monitoring','RailEye v0.5 · Delay-aware environmental evidence')
p.write_text(html,encoding='utf-8')
