"""Print a draft execution wave from GitHub project ledgers; never writes data."""
import sys
from pathlib import Path
import json
from validate import load_view

def plan(root, capacity=4, max_tasks=12, max_steps=20):
    if min(capacity,max_tasks,max_steps) < 1: raise ValueError('Invalid capacity')
    view=load_view(root)
    tasks=view['tasks']; waves=view['waves']
    if view['contract'] != 'framework':
        return {'status':'MANAGER_GATE_REQUIRED','task_ids':[],'groups':{},
                'reason':'Legacy staged waves and project-specific statuses require manager decisions; no automatic wave is proposed.',
                'existing_wave_ids':[w['id'] for w in waves],
                'pending_manager_gates':[w['id'] for w in waves if w['status']=='PENDING_MANAGER_GATE']}
    by_id={t['id']:t for t in tasks}
    active=[w for w in waves if w['status'] in ('DRAFT','READY','IN_PROGRESS','BLOCKED')]
    booked={id for w in active for id in w['task_ids']}
    files={p.casefold() for w in active for id in w['task_ids'] for p in by_id[id]['allowed_files']}
    groups={}; chosen=[]
    for t in sorted(tasks,key=lambda x:(x.get('priority','P9'),x['id'])):
        if t['state']!='READY' or t['id'] in booked or len(chosen)>=max_tasks: continue
        if any(by_id[d]['state']!='COMPLETED' for d in t.get('dependencies',[])): continue
        group=groups.setdefault(t['owner'],[])
        names={p.casefold() for p in t['allowed_files']}
        if len(group)>=capacity or files & names or sum(len(by_id[x].get('steps',[])) or 1 for x in group)+(len(t.get('steps',[])) or 1)>max_steps: continue
        chosen.append(t['id']); group.append(t['id']); files.update(names)
    number=max([int(w['id'].split('-')[1]) for w in waves] or [0])+1
    return {'id':f'WAVE-{number:04d}','status':'DRAFT','task_ids':chosen,'groups':{k:v for k,v in groups.items() if v},'limits':{'per_agent':capacity,'max_tasks':max_tasks,'max_steps_per_agent':max_steps}}

if __name__=='__main__':
    try:
        root=Path(sys.argv[1] if len(sys.argv)>1 else '.')
        print(json.dumps(plan(root),ensure_ascii=False,indent=2))
    except (OSError,ValueError,KeyError,TypeError) as e:
        print('error: '+str(e),file=sys.stderr); sys.exit(1)
