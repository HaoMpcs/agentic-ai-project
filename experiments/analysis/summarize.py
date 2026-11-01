"""Recompute arm metrics from original records/traces; free data requires opt-in."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics


def median(values):
    return statistics.median(values) if values else None


def summarize(folder: Path, *, include_free=False):
    records = [json.loads(p.read_text()) for p in sorted(folder.glob('*.json'))]
    if not records:
        raise ValueError(f'{folder}: no run records')
    if any(r.get('free') for r in records) and not include_free:
        raise ValueError(f'{folder}: scripted/fake data is not evaluation evidence; use --include-free for diagnostics')
    ids = [r['run_id'] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate run IDs')
    configs = {json.dumps([r.get('switches'),r.get('backend'),r.get('settings')],sort_keys=True) for r in records}
    if len(configs) > 1:
        raise ValueError('One arm contains multiple configurations')
    by_task, by_sweep = defaultdict(list), defaultdict(list)
    turns, events, failures = [], Counter(), []
    slow = []
    sequences = set()
    for r in records:
        by_task[r['task']].append(bool(r['passed']))
        by_sweep[str(r['sweep'])].append(bool(r['passed']))
        turns.extend(r.get('turn_latency_s') or [])
        trace_path = folder / (r['run_id'] + '.trace.jsonl')
        if not trace_path.exists():
            raise ValueError(f'Missing original trace: {trace_path}')
        lines = [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
        sequence = []
        first_problem = None
        for number, x in enumerate(lines,1):
            kind = x.get('type')
            if kind == 'tool_call':
                sequence.append(x['name'])
                if x.get('is_error'):
                    events['registry_rejections'] += 1
                    events['error_' + str(x.get('error_class'))] += 1
            elif kind in ('repeat_call','off_plan','tool_retry','model_inflight_timeout'):
                events[kind] += 1
            elif kind == 'plan_validation' and not x['accepted']:
                events['plan_rejections'] += 1
                if 'Orphan' in x.get('reason',''):events['orphan_rejections'] += 1
            elif kind == 'plan' and x.get('revision'):
                events['plan_revisions'] += 1
            elif kind == 'plan_outcome':
                events['plan_outcome_pass' if x['passed'] else 'plan_outcome_fail'] += 1
            elif kind == 'plan_checkpoint':
                events['checkpoint_' + x['name'] + ('_pass' if x['passed'] else '_fail')] += 1
            elif kind == 'draft_critique':
                events['critique_rounds'] += 1
                events['critique_pass' if x['passed'] else 'critique_fail'] += 1
            elif kind == 'plan_execution_diff':
                for field in ('executed','skipped','extra','out_of_order'):
                    events['plan_' + field] += len(x[field])
                events['plan_rejected_attempts'] += len(x.get('rejected', []))
            elif kind == 'end':
                events['end_' + x['terminal_reason']] += 1
            if first_problem is None and (x.get('is_error') or (kind == 'plan_validation' and not x['accepted']) or
                                         (kind == 'plan_outcome' and not x['passed']) or
                                         (kind == 'draft_critique' and not x['passed']) or
                                         (kind == 'end' and x['terminal_reason'] in ('false_finish','agent_step_limit','agent_token_budget','agent_wall_clock'))):
                first_problem = {'trace': str(trace_path), 'line': number, 'event': kind, 'detail': x.get('reason') or x.get('output') or x.get('detail') or x.get('expected')}
        sequences.add(tuple(sequence))
        if not r['passed']:
            failures.append({'run_id':r['run_id'],'task':r['task'],'first_problem':first_problem,
                             'check': r.get('check')})
        if any(t > 10 for t in r.get('turn_latency_s') or []):
            slow.append(r['run_id'])
    count = len(records)
    return {'folder':str(folder), 'data_kind':'fake-model diagnostics' if any(r.get('free') for r in records) else 'real-model runs',
            'runs':count,'passed':sum(bool(r['passed']) for r in records),'pass_rate':sum(bool(r['passed']) for r in records)/count,
            'by_task':{k:{'passed':sum(v),'runs':len(v)} for k,v in sorted(by_task.items())},
            'by_sweep':{k:{'passed':sum(v),'runs':len(v)} for k,v in sorted(by_sweep.items())},
            'tokens':{k:sum(r['tokens'].get(k,0) for r in records) for k in ('input','output','cache_read','cache_write','total')},
            'cost_usd':None if any(r.get('unpriced_calls') for r in records) or events['model_inflight_timeout'] else sum(r['cost_usd'] for r in records),
            'billing_complete':not bool(events['model_inflight_timeout']),
            'median_turn_s':median(turns),'slowest_turn_s':max(turns) if turns else None,
            'median_run_s':median([r['latency_without_wait_s'] for r in records]),
            'turns_above_10s':slow,'events':dict(sorted(events.items())),
            'distinct_tool_sequences':len(sequences),'failures':failures,
            'run_ids':ids,'dirty_runs':sum(bool(r.get('dirty')) for r in records),
            'served_models':sorted({r['model'] for r in records if r.get('model')})}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folders',type=Path,nargs='+')
    parser.add_argument('--include-free',action='store_true')
    args=parser.parse_args()
    try:
        reports=[summarize(f,include_free=args.include_free) for f in args.folders]
    except ValueError as exc:
        parser.error(str(exc))
    result={'arms':reports}
    if len(reports)==2:
        a,b=reports
        if a['by_task'].keys()!=b['by_task'].keys():parser.error('Arm task sets differ')
        result['difference_after_minus_before']={
            'pass_rate':b['pass_rate']-a['pass_rate'],
            'cost_usd':b['cost_usd']-a['cost_usd'] if a['cost_usd'] is not None and b['cost_usd'] is not None else None,
            'total_tokens':b['tokens']['total']-a['tokens']['total'],
            'median_turn_s':b['median_turn_s']-a['median_turn_s']}
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
