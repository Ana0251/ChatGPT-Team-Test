"""Validate .chatgpt-team task and wave ledgers in a GitHub project checkout."""
import json
import sys
from pathlib import Path, PurePosixPath

STATES={'DRAFT','APPROVED','READY','IN_PROGRESS','BLOCKED','READY_FOR_REVIEW','IN_QA','FAILED','COMPLETED','CANCELLED'}

def check(root):
    base=Path(root).resolve()/'.chatgpt-team'
    tasks=json.loads((base/'TASKS.json').read_text(encoding='utf-8'))
    waves=json.loads((base/'WAVES.json').read_text(encoding='utf-8'))
    if tasks.get('mode')!='chatgpt-github' or waves.get('mode')!='chatgpt-github': raise ValueError('Wrong mode')
    rows=tasks.get('tasks'); groups=waves.get('waves')
    if not isinstance(rows,list) or not isinstance(groups,list): raise ValueError('Invalid ledgers')
    by_id={t['id']:t for t in rows}
    if len(by_id)!=len(rows): raise ValueError('Duplicate task id')
    for t in rows:
        if t['state'] not in STATES: raise ValueError('Invalid state')
        if len(t.get('attempts',[]))>3: raise ValueError('Attempt limit exceeded')
        if not isinstance(t.get('history'),list): raise ValueError('Missing history')
        for p in t.get('allowed_files',[]):
            if not isinstance(p,str) or not p or '\\' in p or ':' in p or PurePosixPath(p).is_absolute() or '..' in PurePosixPath(p).parts or PurePosixPath(p).as_posix()!=p: raise ValueError('Invalid file path')
        if any(d not in by_id for d in t.get('dependencies',[])): raise ValueError('Unknown dependency')
    done=set()
    def visit(id,active):
        if id in active: raise ValueError('Dependency cycle')
        if id in done: return
        for d in by_id[id].get('dependencies',[]): visit(d,active|{id})
        done.add(id)
    for id in by_id: visit(id,set())
    wave_ids=set(); reserved=set(); reserved_files=set()
    for w in groups:
        if w['id'] in wave_ids: raise ValueError('Duplicate wave id')
        wave_ids.add(w['id']); files=set()
        if len(w['task_ids'])!=len(set(w['task_ids'])): raise ValueError('Duplicate wave task')
        expected_groups={}
        for id in w['task_ids']:
            if id not in by_id: raise ValueError('Unknown wave task')
            t=by_id[id]
            expected_groups.setdefault(t['owner'],[]).append(id)
            for p in t['allowed_files']:
                key=p.casefold()
                if key in files: raise ValueError('Wave file conflict')
                files.add(key)
            if w['status'] in ('DRAFT','READY','IN_PROGRESS'):
                if id in reserved: raise ValueError('Task in multiple active waves')
                reserved.add(id)
                for p in t['allowed_files']:
                    if p.casefold() in reserved_files: raise ValueError('File conflict across active waves')
                    reserved_files.add(p.casefold())
        if w.get('groups') is not None and w['groups']!=expected_groups: raise ValueError('Wave groups mismatch')
        limits=w.get('limits',{})
        if limits and (len(w['task_ids'])>limits['max_tasks'] or any(len(v)>limits['per_agent'] or sum(len(by_id[x].get('steps',[])) or 1 for x in v)>limits.get('max_steps_per_agent',20) for v in expected_groups.values())): raise ValueError('Wave capacity exceeded')
    return {'tasks':len(rows),'waves':len(groups),'valid':True}

if __name__=='__main__':
    try: print(json.dumps(check(Path(sys.argv[1] if len(sys.argv)>1 else '.'))))
    except (OSError,ValueError,KeyError,TypeError) as e:
        print('error: '+str(e),file=sys.stderr); sys.exit(1)
