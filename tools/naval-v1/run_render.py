#!/usr/bin/env python3
"""Serialized local Blender process ownership, resource admission and raw logs.
No service configuration changes; all children inherit user-999.slice.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path('/srv/hermes-workspace/projects/opensamguk/locks/host-heavy.lock')
CGROUP = Path('/sys/fs/cgroup/user.slice/user-999.slice')


def resources():
    current = int((CGROUP/'memory.current').read_text())
    maximum = (CGROUP/'memory.max').read_text().strip()
    available = next(int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
    return {'cgroupMemoryCurrent': current, 'cgroupMemoryMax': maximum,
            'cgroupHeadroom': int(maximum)-current if maximum != 'max' else available,
            'hostMemAvailable': available, 'cgroup': Path('/proc/self/cgroup').read_text().strip()}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--build',action='store_true')
    p.add_argument('--audit',action='store_true')
    p.add_argument('--asset')
    p.add_argument('--timeout',type=int,default=1800)
    p.add_argument('--lock-wait',type=int,default=0)
    args=p.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=True)
    command=['blender','--background','--factory-startup','--threads','1','--python-exit-code','1','--python',str(ROOT/'tools/naval-v1/blender_pipeline.py'),'--']
    command += ['--audit'] if args.audit else (['--build','--render'] if args.build else ['--render'])
    if args.asset: command += ['--asset',args.asset]
    record={'utcStart':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':command,'cwd':str(ROOT),'before':resources(),'status':'NOT_RUN','productQA':'NOT_RUN','gamePNGCount':0}
    child=None
    def cancel(signum,frame):
        raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM,cancel)
    signal.signal(signal.SIGINT,cancel)
    def lock_timeout(signum,frame):
        raise TimeoutError('shared heavy1 lock wait expired')
    with LOCK.open('a') as lock:
        try:
            if args.lock_wait:
                signal.signal(signal.SIGALRM,lock_timeout)
                signal.alarm(args.lock_wait)
                try: fcntl.flock(lock,fcntl.LOCK_EX)
                finally: signal.alarm(0)
            else:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            record['before']=resources()
            # Measured admission floor for small CPU-only scenes; never relax host/cgroup limits.
            if min(record['before']['cgroupHeadroom'],record['before']['hostMemAvailable']) < 384*1024**2:
                raise RuntimeError('insufficient 384MiB render headroom; do not bypass budget')
            env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MALLOC_ARENA_MAX='2')
            record['renderScriptSHA256']=hashlib.sha256((ROOT/'tools/naval-v1/blender_pipeline.py').read_bytes()).hexdigest()
            with (args.evidence/'blender.log').open('w') as log:
                child=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                record['pid']=child.pid
                started=time.monotonic()
                samples=[]
                while child.poll() is None:
                    if time.monotonic()-started>args.timeout: raise TimeoutError('owned Blender timeout')
                    state=resources()
                    if min(state['cgroupHeadroom'],state['hostMemAvailable']) < 96*1024**2:
                        raise RuntimeError('live budget below 96MiB safety margin; stopping owned Blender')
                    try:
                        state['childRSSKiB']=int(next(x for x in Path(f'/proc/{child.pid}/status').read_text().splitlines() if x.startswith('VmRSS:')).split()[1])
                    except (OSError,StopIteration): pass
                    samples.append(state)
                    time.sleep(2)
                record['exitCode']=child.returncode
                record['status']='PASS' if child.returncode==0 else 'FAIL'
                record['resourceSamples']=samples
        except (OSError,RuntimeError,TimeoutError,KeyboardInterrupt) as exc:
            record['error']=str(exc) or type(exc).__name__
            record['status']='FAIL' if child else 'NOT_RUN'
        finally:
            if child:
                # This child has its own session/process group: never kill unrelated processes.
                try: os.killpg(child.pid,signal.SIGTERM)
                except ProcessLookupError: pass
                try: child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL); child.wait(timeout=5)
                try: os.killpg(child.pid,0); record['ownedGroupGone']=False
                except ProcessLookupError: record['ownedGroupGone']=True
                record['exitCode']=child.returncode
            else: record['ownedGroupGone']=True
            record['after']=resources()
            record['utcEnd']=datetime.datetime.now(datetime.timezone.utc).isoformat()
            (args.evidence/'render-run.json').write_text(json.dumps(record,indent=2)+'\n')
            print(json.dumps({k:v for k,v in record.items() if k!='resourceSamples'},indent=2))
    return 0 if record['status']=='PASS' and record['ownedGroupGone'] else 1


if __name__=='__main__': raise SystemExit(main())
