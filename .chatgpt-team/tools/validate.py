"""Validate both the framework and the extended 1.2 GitHub ledger contracts.

The compatibility view is read-only. It never renames project statuses or fields on disk.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath

STATES = {'DRAFT', 'APPROVED', 'READY', 'IN_PROGRESS', 'BLOCKED',
          'READY_FOR_REVIEW', 'IN_QA', 'FAILED', 'COMPLETED', 'CANCELLED'}
SENSITIVE_PATH = re.compile(
    r'(?i)(?:^|/)(?:api|migrations?|schemas?|database|db|infra(?:structure)?|architecture|\.github)(?:/|\.|$)'
)
ACTIVE = {'DRAFT', 'READY', 'IN_PROGRESS', 'BLOCKED'}


def _mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError(label + ' must be an object')
    return value


def _list(value, label):
    if not isinstance(value, list):
        raise ValueError(label + ' must be an array')
    return value


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' must be a nonempty string')
    return value


def _path(value, label):
    _text(value, label)
    path = PurePosixPath(value)
    if ('\\' in value or ':' in value or '\x00' in value or path.is_absolute()
            or '..' in path.parts or path.as_posix() != value):
        raise ValueError('Invalid file path: ' + label + ' must be a safe project-relative POSIX path')
    return value


def _strings(value, label):
    for item in _list(value, label):
        _text(item, label + ' item')
    return value


def _task_view(row, index):
    task = _mapping(row, f'task #{index}')
    task_id = _text(task.get('id'), f'task #{index} id')
    has_state, has_status = 'state' in task, 'status' in task
    if has_state == has_status:
        raise ValueError(f'task {task_id}: exactly one of state or status is required')
    kind = 'framework' if has_state else 'legacy'
    state = _text(task['state' if has_state else 'status'], f'task {task_id} status')
    if has_state and state not in STATES:
        raise ValueError(f'task {task_id}: invalid framework state {state}')
    _text(task.get('owner'), f'task {task_id} owner')
    if kind == 'framework':
        if 'depends_on' in task or 'allowed_paths' in task:
            raise ValueError(f'task {task_id}: conflicting dependency or path field families')
        dependencies = _strings(task.get('dependencies', []), f'task {task_id} dependencies')
        paths = _strings(task.get('allowed_files', []), f'task {task_id} allowed_files')
        _strings(task.get('steps', []), f'task {task_id} steps')
        _list(task.get('attempts', []), f'task {task_id} attempts')
        if len(task.get('attempts', [])) > 3:
            raise ValueError(f'task {task_id}: attempt limit exceeded')
        history = _list(task.get('history'), f'task {task_id} history')
    else:
        if 'dependencies' in task or 'allowed_files' in task:
            raise ValueError(f'task {task_id}: conflicting dependency or path field families')
        dependencies = _strings(task.get('depends_on'), f'task {task_id} depends_on')
        paths = _strings(task.get('allowed_paths'), f'task {task_id} allowed_paths')
        history = _list(task.get('history', []), f'task {task_id} history')
        if 'attempts' in task:
            _list(task['attempts'], f'task {task_id} attempts')
        if 'start_authorized' in task and not isinstance(task['start_authorized'], bool):
            raise ValueError(f'task {task_id}: start_authorized must be boolean')
        if 'validation_status' in task:
            _text(task['validation_status'], f'task {task_id} validation_status')
        if 'evidence_refs' in task:
            _strings(task['evidence_refs'], f'task {task_id} evidence_refs')
        for key in ('project', 'release', 'priority', 'acceptance_criteria',
                    'evidence_required'):
            if key in task:
                _text(task[key], f'task {task_id} {key}')
        for key in ('mandatory_amendments', 'completed_on'):
            if key in task and not isinstance(task[key], str):
                raise ValueError(f'task {task_id}: {key} must be text')
        for key in ('notes', 'dependency_policy'):
            if key in task and task[key] is not None and not isinstance(task[key], str):
                raise ValueError(f'task {task_id}: {key} must be text or null')
        if 'wave' in task:
            _text(task['wave'], f'task {task_id} wave')
        if 'waves' in task:
            _strings(task['waves'], f'task {task_id} waves')
            if len(task['waves']) != len(set(task['waves'])):
                raise ValueError(f'task {task_id}: duplicate wave membership')
            if 'wave' in task and task['wave'] not in task['waves']:
                raise ValueError(f'task {task_id}: primary wave missing from waves')
    for path in paths:
        _path(path, f'task {task_id} path')
    if len(paths) != len(set(p.casefold() for p in paths)):
        raise ValueError(f'task {task_id}: duplicate allowed path')
    for dep in dependencies:
        if dep == task_id:
            raise ValueError(f'task {task_id}: self dependency')
    for item in history:
        _mapping(item, f'task {task_id} history item')
    reports = _list(task.get('reports', []), f'task {task_id} reports')
    for item in reports:
        _mapping(item, f'task {task_id} report')
    review = task.get('review_policy')
    if review is not None:
        if review not in ('direct_qa', 'coordinator_required'):
            raise ValueError(f'task {task_id}: invalid review policy')
        review_history = _list(task.get('review_history', []), f'task {task_id} review_history')
        for item in review_history:
            _mapping(item, f'task {task_id} review decision')
        if review == 'direct_qa':
            if task.get('review_risks') != [] or not isinstance(task.get('review_reason'), str) or not task['review_reason'].strip():
                raise ValueError(f'task {task_id}: direct QA needs an explicit low-risk decision')
            if any(SENSITIVE_PATH.search(p) for p in paths):
                raise ValueError(f'task {task_id}: sensitive path requires coordinator')
            if state != 'DRAFT' and (not review_history or review_history[-1].get('actor') != 'manager'):
                raise ValueError(f'task {task_id}: manager review decision required')
        if review_history and review_history[-1].get('policy') != review:
            raise ValueError(f'task {task_id}: review policy differs from decision history')
        if state in ('READY_FOR_REVIEW', 'IN_QA', 'COMPLETED'):
            if not any(r.get('actor') == task['owner'] for r in reports):
                raise ValueError(f'task {task_id}: owner report required')
        if state in ('IN_QA', 'COMPLETED') and review == 'coordinator_required':
            entered = next((h.get('at') for h in reversed(history) if h.get('to') == 'READY_FOR_REVIEW'), None)
            if not entered or not any(r.get('actor') == 'coordinator' and r.get('at', '') >= entered for r in reports):
                raise ValueError(f'task {task_id}: fresh coordinator report required')
        if state == 'IN_QA' and review == 'direct_qa':
            if not any(h.get('to') == 'IN_QA' and h.get('actor') == 'qa' for h in history):
                raise ValueError(f'task {task_id}: QA must accept direct review')
        if state == 'COMPLETED':
            entered = next((h.get('at') for h in reversed(history) if h.get('to') == 'IN_QA'), None)
            if not entered or not any(r.get('actor') == 'qa' and r.get('verdict') == 'PASS'
                                      and r.get('at', '') >= entered for r in reports):
                raise ValueError(f'task {task_id}: fresh QA PASS evidence required')
    return {'id': task_id, 'kind': kind, 'state': state, 'owner': task['owner'],
            'priority': task.get('priority', 'P9'), 'dependencies': dependencies,
            'allowed_files': paths, 'steps': task.get('steps', []),
            'approval_id': task.get('approval_id'), 'wave': task.get('wave'),
            'waves': task.get('waves'), 'start_authorized': task.get('start_authorized', False),
            'review_policy': review or 'coordinator_required'}


def _acyclic(dependencies, label):
    done = set()
    def visit(item, active):
        if item in active:
            raise ValueError(f'{label}: dependency cycle at {item}')
        if item in done:
            return
        for dep in dependencies[item]:
            if dep not in dependencies:
                raise ValueError(f'{label}: unknown dependency {dep}')
            visit(dep, active | {item})
        done.add(item)
    for item in dependencies:
        visit(item, set())


def load_view(root):
    base = Path(root).resolve() / '.chatgpt-team'
    tasks_data = _mapping(json.loads((base / 'TASKS.json').read_text(encoding='utf-8')), 'TASKS.json')
    waves_data = _mapping(json.loads((base / 'WAVES.json').read_text(encoding='utf-8')), 'WAVES.json')
    if tasks_data.get('mode') != 'chatgpt-github' or waves_data.get('mode') != 'chatgpt-github':
        raise ValueError('Wrong mode')
    rows = _list(tasks_data.get('tasks'), 'TASKS.json tasks')
    raw_waves = _list(waves_data.get('waves'), 'WAVES.json waves')
    tasks = [_task_view(row, i + 1) for i, row in enumerate(rows)]
    by_id = {task['id']: task for task in tasks}
    if len(by_id) != len(tasks):
        raise ValueError('Duplicate task id')
    _acyclic({task['id']: task['dependencies'] for task in tasks}, 'tasks')
    approvals = _list(tasks_data.get('approvals', []), 'TASKS.json approvals')
    approval_ids = []
    for approval in approvals:
        approval = _mapping(approval, 'approval')
        approval_ids.append(_text(approval.get('id'), 'approval id'))
        _text(approval.get('status', 'RECORDED'), 'approval status')
        if 'approved_by' in approval:
            _text(approval['approved_by'], 'approval approved_by')
        for key in ('decision_ids', 'task_proposal_ids', 'wave_proposal_ids'):
            if key in approval:
                _strings(approval[key], 'approval ' + key)
        for key in ('registered_task_count', 'registered_wave_count'):
            if key in approval and (not isinstance(approval[key], int) or approval[key] < 0):
                raise ValueError('approval ' + key + ' must be nonnegative')
    if len(approval_ids) != len(set(approval_ids)):
        raise ValueError('Duplicate approval id')
    approval_set = set(approval_ids)
    for task in tasks:
        if task['approval_id'] is not None and task['approval_id'] not in approval_set:
            raise ValueError(f"task {task['id']}: unknown approval {task['approval_id']}")
    waves = []
    wave_ids = set()
    membership = {}
    reserved_tasks = set()
    reserved_paths = set()
    sequences = set()
    for index, raw in enumerate(raw_waves, 1):
        wave = _mapping(raw, f'wave #{index}')
        wave_id = _text(wave.get('id'), f'wave #{index} id')
        if wave_id in wave_ids:
            raise ValueError('Duplicate wave id: ' + wave_id)
        wave_ids.add(wave_id)
        task_ids = _strings(wave.get('task_ids'), f'wave {wave_id} task_ids')
        if len(task_ids) != len(set(task_ids)):
            raise ValueError('Duplicate task in wave: ' + wave_id)
        for task_id in task_ids:
            if task_id not in by_id:
                raise ValueError(f'wave {wave_id}: unknown task {task_id}')
            membership.setdefault(task_id, []).append(wave_id)
        legacy = (any(by_id[x]['kind'] == 'legacy' for x in task_ids)
                  or ('sequence' in wave and 'groups' not in wave))
        status = _text(wave.get('status'), f'wave {wave_id} status')
        if wave.get('approval_id') is not None and wave['approval_id'] not in approval_set:
            raise ValueError(f'wave {wave_id}: unknown approval {wave["approval_id"]}')
        if legacy:
            deps = _strings(wave.get('depends_on', []), f'wave {wave_id} depends_on')
            if 'sequence' in wave and (not isinstance(wave['sequence'], int) or wave['sequence'] < 0):
                raise ValueError(f'wave {wave_id}: invalid sequence')
            if 'sequence' in wave:
                if wave['sequence'] in sequences:
                    raise ValueError(f'wave {wave_id}: duplicate sequence')
                sequences.add(wave['sequence'])
            if 'entry_authorized' in wave and not isinstance(wave['entry_authorized'], bool):
                raise ValueError(f'wave {wave_id}: invalid entry_authorized')
            if 'evidence_refs' in wave:
                _strings(wave['evidence_refs'], f'wave {wave_id} evidence_refs')
            for key in ('name', 'entry_criteria', 'exit_criteria', 'policy'):
                if key in wave:
                    _text(wave[key], f'wave {wave_id} {key}')
            for key in ('started_at', 'completed_at', 'completed_on'):
                if key in wave and wave[key] is not None and not isinstance(wave[key], str):
                    raise ValueError(f'wave {wave_id}: {key} must be text or null')
            if 'completion_decision_id' in wave and wave['completion_decision_id'] not in approval_set:
                raise ValueError(f'wave {wave_id}: unknown completion decision')
        else:
            if status not in STATES:
                raise ValueError(f'wave {wave_id}: invalid framework status {status}')
            deps = _strings(wave.get('depends_on', []), f'wave {wave_id} depends_on')
            files = set()
            groups = {}
            for task_id in task_ids:
                task = by_id[task_id]
                groups.setdefault(task['owner'], []).append(task_id)
                names = {p.casefold() for p in task['allowed_files']}
                if files & names:
                    raise ValueError(f'wave {wave_id}: file conflict')
                files.update(names)
                if status in ACTIVE:
                    if task_id in reserved_tasks:
                        raise ValueError(f'task {task_id}: in multiple active framework waves')
                    reserved_tasks.add(task_id)
                    if names & reserved_paths:
                        raise ValueError(f'wave {wave_id}: file conflict across active waves')
                    reserved_paths.update(names)
            if wave.get('groups') is not None and wave['groups'] != groups:
                raise ValueError(f'wave {wave_id}: groups mismatch')
            limits = wave.get('limits', {})
            if limits:
                _mapping(limits, f'wave {wave_id} limits')
                if any(not isinstance(limits.get(key), int) or limits[key] < 1
                       for key in ('per_agent', 'max_tasks', 'max_steps_per_agent')):
                    raise ValueError(f'wave {wave_id}: invalid capacity')
                if len(task_ids) > limits['max_tasks'] or any(
                    len(group) > limits['per_agent'] or
                    sum(len(by_id[x]['steps']) or 1 for x in group) > limits['max_steps_per_agent']
                    for group in groups.values()
                ):
                    raise ValueError(f'wave {wave_id}: capacity exceeded')
        waves.append({'id': wave_id, 'kind': 'legacy' if legacy else 'framework',
                      'status': status, 'task_ids': task_ids, 'depends_on': deps})
    _acyclic({wave['id']: wave['depends_on'] for wave in waves}, 'waves')
    for task in tasks:
        if task['kind'] != 'legacy':
            continue
        actual = membership.get(task['id'], [])
        declared = task['waves']
        if declared is not None and set(declared) != set(actual):
            raise ValueError(f"task {task['id']}: wave membership differs from WAVES.json")
        if task['wave'] is not None and task['wave'] not in actual:
            raise ValueError(f"task {task['id']}: primary wave not found in WAVES.json")
    kinds = {task['kind'] for task in tasks} | {wave['kind'] for wave in waves}
    contract = 'mixed' if len(kinds) > 1 else next(iter(kinds), 'framework')
    return {'contract': contract, 'tasks': tasks, 'waves': waves,
            'approvals': approvals, 'raw_tasks': tasks_data, 'raw_waves': waves_data}


def check(root):
    view = load_view(root)
    return {'tasks': len(view['tasks']), 'waves': len(view['waves']), 'valid': True,
            'contract': view['contract'],
            'task_statuses': dict(Counter(t['state'] for t in view['tasks'])),
            'wave_statuses': dict(Counter(w['status'] for w in view['waves'])),
            'approvals': len(view['approvals'])}


if __name__ == '__main__':
    try:
        print(json.dumps(check(Path(sys.argv[1] if len(sys.argv) > 1 else '.')), ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('error: ' + str(exc), file=sys.stderr)
        sys.exit(1)
