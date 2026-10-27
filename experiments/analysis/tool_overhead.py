"""Three actual metered calls with identical text; never estimate provider tokens."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from agent.tools import Registry
from harness import ROOT, runtime
from harness.settings import load_settings


def schema_stats(tools):
    optional=unions=depth=0
    def visit(spec,level=0):
        nonlocal optional,unions,depth
        depth=max(depth,level)
        if isinstance(spec.get('type'),list):unions+=1
        if spec.get('type')=='object':
            optional+=len(set(spec.get('properties',{}))-set(spec.get('required',[])))
        for child in spec.get('properties',{}).values():visit(child,level+1)
        if 'items' in spec:visit(spec['items'],level+1)
    selected=[t for t in tools if t.get('strict')]
    for tool in selected:visit(tool['input_schema'])
    return {'strict_tools':len(selected),'optional_parameters':optional,'union_typed_parameters':unions,'deepest_schema_nesting':depth}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'experiments/tool_definitions/measurement.json')
    parser.add_argument('--schema-only',action='store_true')
    args=parser.parse_args()
    runtime.configure()
    registry=Registry('tool-overhead',[])
    definitions=registry.definitions()
    if args.schema_only:
        print(json.dumps(schema_stats(definitions),indent=2));return
    settings=load_settings()
    if not settings.provider or not settings.model:
        parser.error('Configure a real provider/model/key before measuring; no measurement was created.')
    client=runtime.client('tool-overhead')
    if getattr(client.backend,'free',False):parser.error('Fake models cannot measure API token overhead.')
    first=json.loads((ROOT/'experiments/tool_definitions/first_draft.json').read_text())
    rows=[]
    for label,tools in [('no_tools',[]),('first_draft',first),('rewritten',definitions)]:
        response=client.create(system='Reply briefly. Do not call any tool.',messages=[{'role':'user','content':'Acknowledge this test.'}],tools=tools)
        runtime.trace('tool-overhead').model_call(len(rows)+1,response,purpose=label,content=response.content)
        rows.append({'label':label,'model':response.model,'reported_input_tokens':response.usage.prompt_tokens,
                     'cost_usd':response.cost_usd,'usage':response.usage.as_dict()})
    base=rows[0]['reported_input_tokens']
    for row in rows:row['additional_input_tokens']=row['reported_input_tokens']-base
    data={'settings_digest':settings.digest(),'rows':rows,'schema':schema_stats(definitions),
          'method':'Same message and settings; provider-reported prompt tokens including cached input. Tool calls are forbidden by instruction.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data,indent=2))


if __name__=='__main__':main()
