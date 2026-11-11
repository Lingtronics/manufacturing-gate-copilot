from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.persistence.store import Store
from app.services.evidence.index import load_fixtures,snapshot
from app.services.assessment.engine import assess
from app.services.value.calculator import value_case
from app.services.report import executive_report
from app.services.miro.scene import build_board_scene,render_html
from app.domain.models import Project

root=Path(__file__).resolve().parents[1]
s=Store(':memory:');load_fixtures(s);p=Project.model_validate(s.all('project')[0]);a=assess(snapshot(s,p.id));v=value_case(s,p.id)
(root/'docs/executive-readout.md').write_text(executive_report(a,p,v),encoding='utf-8')
(root/'docs/board-preview.html').write_text(render_html(build_board_scene(a,p,v)),encoding='utf-8')
print('Generated synthetic executive report and standalone local board preview.')
