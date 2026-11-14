"""Read-only administrative queues for a ChatGPT GitHub project."""
import json
import sys
from collections import Counter
from pathlib import Path
from validate import load_view

def status(root):
    view=load_view(root)
    tasks=view['tasks']; waves=view['waves']
    by_id={t['id']:t for t in tasks}
    return {
        'review_queue':[t['id'] for t in tasks if t['state']=='READY_FOR_REVIEW'],
        'qa_queue':[t['id'] for t in tasks if t['state']=='IN_QA' or
                    (t['state']=='READY_FOR_REVIEW' and t['review_policy']=='direct_qa')],
        'coordinator_queue':[t['id'] for t in tasks if t['state']=='READY_FOR_REVIEW' and
                             t['review_policy']=='coordinator_required'],
        'prepare_ready':[t['id'] for t in tasks if t['kind']=='framework' and t['state']=='APPROVED' and t.get('approval_id') and
                         all(by_id[d]['state']=='COMPLETED' for d in t['dependencies'])],
        'blocked':[t['id'] for t in tasks if t['state'] in ('BLOCKED','FAILED')],
        'active_waves':[w['id'] for w in waves if w['status'] not in ('COMPLETED','CANCELLED')],
        'completed':[t['id'] for t in tasks if t['state']=='COMPLETED'],
        'authorized_not_started':[t['id'] for t in tasks if t['kind']=='legacy' and
                                  t['state']=='AUTHORIZED_NOT_STARTED' and t['start_authorized']],
        'manager_gates':[w['id'] for w in waves if w['status']=='PENDING_MANAGER_GATE'],
        'raw_task_statuses':dict(Counter(t['state'] for t in tasks)),
        'contract':view['contract']
    }

if __name__=='__main__':
    try: print(json.dumps(status(Path(sys.argv[1] if len(sys.argv)>1 else '.')),ensure_ascii=False,indent=2))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('error: '+str(exc),file=sys.stderr); sys.exit(1)
