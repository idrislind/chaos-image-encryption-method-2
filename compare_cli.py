"""Reproducible, repeat-trial experimental A/B comparison of Method 1 vs 2.

Uses the same image, randomly generated session key and nonce for both methods
within each trial. Outputs raw trials and group aggregate (population std).
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from chaos_image_encryption.io.image_io import load_image
from chaos_image_encryption.comparison import compare_methods


def main():
    p=argparse.ArgumentParser(description='Controlled comparison Hénon vs 2DLMUTF')
    p.add_argument('--image',required=True)
    p.add_argument('--trials',type=int,default=5)
    p.add_argument('--out-dir',default='results/compare_methods')
    a=p.parse_args()
    if a.trials < 1 or a.trials>500:
        p.error('--trials must be between 1 and 500')
    image,_=load_image(a.image)
    out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for i in range(1,a.trials+1):
        key,nonce=os.urandom(32),os.urandom(16)
        result=compare_methods(image,key,nonce)
        for method,v in result.items():
            corr=v['correlation_cipher']
            rows.append({'trial':i,'method':method,
                         'exact_match':v['exact_match'],
                         'entropy_cipher':v['entropy_cipher'],
                         'npcr_percent':v['npcr_percent'],
                         'uaci_percent':v['uaci_percent'],
                         'correlation_h':corr['horizontal'],
                         'correlation_v':corr['vertical'],
                         'correlation_d':corr['diagonal'],
                         'encrypt_ms':v['encrypt_ms'],
                         'decrypt_ms':v['decrypt_ms']})
        print(f'[{i}/{a.trials}] complete',flush=True)
    with (out/'trials.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    aggregate=[]
    for method in dict.fromkeys(r['method'] for r in rows):
        rr=[r for r in rows if r['method']==method]
        item={'method':method,'trials':len(rr),'exact_match_rate_percent':100*sum(r['exact_match'] for r in rr)/len(rr)}
        for field in ['entropy_cipher','npcr_percent','uaci_percent','correlation_h',
                      'correlation_v','correlation_d','encrypt_ms','decrypt_ms']:
            avalues=[r[field] for r in rr]
            item[field+'_mean']=statistics.fmean(avalues)
            item[field+'_std']=statistics.pstdev(avalues) if len(avalues)>1 else 0.0
        aggregate.append(item)
    with (out/'summary.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(aggregate[0]));w.writeheader();w.writerows(aggregate)
    (out/'summary.json').write_text(json.dumps(aggregate,indent=2),encoding='utf8')
    print(f'Raw trials: {out/"trials.csv"}\nSummary: {out/"summary.csv"}\nJSON: {out/"summary.json"}')

if __name__=='__main__': main()
