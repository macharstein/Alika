"""Run only the committed 50/200-day SQLite memory diagnostics (never production)."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    records=[]
    for size in (1000,500):
        for days in (50,200):
            for workers in (1,4):
                plan=ROOT/f'data/check_plans/memory_{size}_{days}_{workers}.json'
                payload=json.loads(plan.read_text())
                db=(plan.parent/payload['splits']['train']['database']).resolve()
                metrics=db.with_suffix('.metrics.json')
                if metrics.exists() and json.loads(metrics.read_text()).get('complete'):
                    record=json.loads(metrics.read_text())
                else:
                    command=[sys.executable,'-m','lionsim.build_dataset','--plan',str(plan),
                             '--workers',str(workers),'--only','train']
                    if db.exists() or db.with_suffix('.meta.json').exists():
                        command.append('--resume')
                    subprocess.run(command,cwd=ROOT,check=True)
                    record=json.loads(metrics.read_text())
                    if record['new_days']!=days:
                        raise RuntimeError('Interrupted benchmark resumed safely, but timing is partial; label it explicitly before comparing.')
                subprocess.run([sys.executable,'-m','lionsim.verify_db','--plan',str(plan),'--only','train'],cwd=ROOT,check=True)
                records.append(record)
                destination=ROOT/'outputs/sqlite_memory/measurements.json'
                temporary=destination.with_suffix('.tmp')
                temporary.write_text(json.dumps(records,indent=2)+'\n')
                temporary.replace(destination)
                print(f'MEASURED size={size}, days={days}, workers={workers}: '+json.dumps(record),flush=True)


if __name__=='__main__':
    main()
