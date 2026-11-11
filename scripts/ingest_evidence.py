from pathlib import Path
import sys
import argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.persistence.store import Store
from app.services.evidence.index import load_fixtures
from app.services.evidence.ingest import ingest_document
from app.domain.models import EvidenceStatus

parser=argparse.ArgumentParser(description='Ingest a local synthetic JSON/Markdown evidence revision. Does not publish.')
parser.add_argument('source',type=Path)
parser.add_argument('--db',default='data/copilot.sqlite3')
parser.add_argument('--id',required=True)
parser.add_argument('--revision',required=True)
parser.add_argument('--title',required=True)
parser.add_argument('--requirement',action='append',required=True)
parser.add_argument('--status',choices=[s.value for s in EvidenceStatus],default='PARTIAL')
args=parser.parse_args()
store=Store(args.db);load_fixtures(store)
doc=ingest_document(store,args.source,args.id,args.revision,args.title,args.requirement,EvidenceStatus(args.status))
# Evidence IDs already in the policy are immediately picked up by the next assessment.
for approval in store.all('approval'):
    if approval['status']!='SUPERSEDED':
        approval['status']='SUPERSEDED';store.put('approval',approval['id'],approval)
        store.audit('local-cli','approval_superseded',approval['id'],'local-ingestion')
store.audit('local-cli','source_ingested',doc.id,'local-ingestion',revision=doc.revision,content_hash=doc.content_hash)
print(f'Ingested {doc.id} rev {doc.revision} ({doc.content_hash}). Run a fresh assessment.')
