#!/usr/bin/env python3
"""Real bounded Linux fork fixtures, NOT Blender or product QA.

Uses the actual shared heavy1 lock, supervisor, signals, pidfds and /proc.
Exception injection affects only the resource observer, never cleanup behavior.
Set NAVAL_TEST_EVIDENCE to preserve raw per-case logs/records.
"""
import ctypes
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from owned_process import process_table

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT/'tools/naval-v1/run_render.py'
LOCK = Path('/srv/hermes-workspace/projects/opensamguk/locks/host-heavy.lock')
FIXTURE = '''#!/usr/bin/python3
import json, os, signal, time
from pathlib import Path
mode = os.environ['FIXTURE_MODE']
if mode == 'clean':
    print('fixture clean exit', flush=True)
    raise SystemExit(0)
pid = os.fork()
if pid == 0:
    if mode == 'escape': os.setsid()
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    fields = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()
    info = Path(os.environ['FIXTURE_INFO'])
    info.with_suffix('.pending').write_text(json.dumps({
        'pid': os.getpid(), 'pgid': os.getpgrp(), 'sid': os.getsid(0),
        'leader': os.getppid(), 'starttime': int(fields[19])}))
    info.with_suffix('.pending').replace(info)
    print('fixture descendant ready', flush=True)
    if mode == 'zombie': os._exit(0)
    while True: time.sleep(.1)
while not Path(os.environ['FIXTURE_INFO']).exists(): time.sleep(.01)
if mode in ('normal', 'escape', 'zombie', 'cleanup-exception'): os._exit(0)
if mode == 'failure': os._exit(7)
if mode == 'ignore-all': signal.signal(signal.SIGTERM, signal.SIG_IGN)
while True: time.sleep(.1)
'''
EXCEPTION_WRAPPER = '''import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv.pop(1))
import run_render
if __import__('os').environ['FIXTURE_MODE'] == 'cleanup-exception':
    original_observe = run_render.OwnedTree.observe
    failed = False
    def observe_once_failed(self):
        global failed
        if not failed:
            failed = True
            raise OSError('injected cleanup observation error')
        return original_observe(self)
    run_render.OwnedTree.observe = observe_once_failed
    raise SystemExit(run_render.main())
original = run_render.resources
calls = 0
def fail_observation():
    global calls
    calls += 1
    if calls == 3:
        deadline = time.monotonic()+10
        while not Path(__import__('os').environ['FIXTURE_INFO']).exists():
            if time.monotonic()>deadline: raise RuntimeError('fixture not ready')
            time.sleep(.01)
        raise ValueError('injected resource observer exception after real fork')
    return original()
run_render.resources = fail_observation
raise SystemExit(run_render.main())
'''


class ActualOwnership(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Test-only fallback reaper if a regression causes a supervisor to leak.
        assert ctypes.CDLL(None).prctl(36, 1, 0, 0, 0) == 0
        cls.temporary = None
        if os.environ.get('NAVAL_TEST_EVIDENCE'):
            cls.output = Path(os.environ['NAVAL_TEST_EVIDENCE']).resolve()
        else:
            cls.temporary = tempfile.TemporaryDirectory(dir=os.environ['TMPDIR'])
            cls.output = Path(cls.temporary.name)
        cls.output.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        if cls.temporary:
            cls.temporary.cleanup()

    def exercise(self, mode, expected, cancel=False, exception=False, escalation=True):
        evidence = self.output/self._testMethodName
        evidence.mkdir(exist_ok=True)
        fixture = evidence/'blender'
        fixture.write_text(FIXTURE)
        fixture.chmod(0o755)
        info_path = evidence/'child.json'
        wrapper = evidence/'inject_exception.py'
        wrapper.write_text(EXCEPTION_WRAPPER)
        env = dict(os.environ, PATH=str(evidence)+os.pathsep+os.environ['PATH'],
                   FIXTURE_INFO=str(info_path), FIXTURE_MODE=mode)
        command = [sys.executable, str(RUNNER)]
        if exception:
            command = [sys.executable, str(wrapper), str(RUNNER.parent)]
        command += ['--audit', '--evidence', str(evidence), '--lock-wait', '180',
                    '--timeout', '1' if mode in ('timeout', 'ignore-all') else '30']
        sentinel = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(300)'])
        proc = None
        info = None
        observations = []
        result = {'fixtureOnly': True, 'productQA': 'NOT_RUN', 'command': command}
        try:
            with (evidence/'supervisor.log').open('w') as log, LOCK.open('a') as lock:
                proc = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT)
                deadline = time.monotonic()+220
                next_cancel = 0
                while proc.poll() is None:
                    if info is None and info_path.exists():
                        info = json.loads(info_path.read_text())

                    if info is not None:
                        table = process_table()
                        live = info['pid'] in table
                        try:
                            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            free = True
                            fcntl.flock(lock, fcntl.LOCK_UN)
                        except BlockingIOError:
                            free = False
                        leader = table.get(info['leader'])
                        observations.append({'childPresent': live, 'heavyLockFree': free,
                                             'leaderState': leader['state'] if leader else None})
                        if cancel and time.monotonic() >= next_cancel:
                            proc.send_signal(signal.SIGTERM)
                            next_cancel = time.monotonic()+.2
                    if time.monotonic()>deadline:
                        self.fail('bounded fixture supervisor timed out')
                    time.sleep(.03)
                record = json.loads((evidence/'render-run.json').read_text())
                if info is None and info_path.exists():
                    info = json.loads(info_path.read_text())
                result.update(supervisorExit=proc.returncode, record=record,
                              observations=observations, unrelatedSentinelAlive=sentinel.poll() is None)
                self.assertEqual(proc.returncode, expected)
                self.assertTrue(record['heavyLockAcquired'])
                self.assertTrue(record['heavyLockReleaseReady'])
                self.assertTrue(record['ownedGroupGone'])
                self.assertTrue(record['ownedTreeGone'])
                self.assertTrue(record['cleanup']['confirmed'])
                self.assertEqual(record['cleanup']['killEscalated'], escalation)
                self.assertEqual(record['status'], 'PASS' if expected == 0 else 'FAIL')
                self.assertFalse(any(o['childPresent'] and o['heavyLockFree'] for o in observations))
                if mode != 'clean':
                    assert info is not None, 'actual forked descendant must be recorded'
                    if mode != 'zombie':
                        self.assertTrue(observations, 'actual descendant was observed')
                        self.assertTrue(any(o['childPresent'] and not o['heavyLockFree'] for o in observations))
                    self.assertNotIn(info['pid'], process_table())
                    self.assertIn(info['pid'], [r['pid'] for r in record['cleanup']['reapedDescendants']])
                    if mode in ('normal', 'failure', 'timeout', 'escape'):
                        self.assertTrue(any(o['childPresent'] and o['leaderState']=='Z'
                                            and not o['heavyLockFree'] for o in observations),
                                        'leader PID/PGID reservation must outlive the leader')
                with self.assertRaises(ProcessLookupError): os.killpg(record['pid'], 0)
                self.assertIsNone(sentinel.poll(), 'unrelated process must not be signalled')
                if cancel:
                    self.assertGreater(len(record['cancellationSignals']), 2)
                if exception and mode != 'cleanup-exception':
                    self.assertIn('injected resource observer exception', record['error'])
                if mode == 'cleanup-exception':
                    self.assertEqual(record['exitCode'], 0, 'cleanup failure must override leader success')
                    self.assertIn('injected cleanup observation error', record['cleanup']['error'])
                result['passed'] = True
        finally:
            # Only our test-owned processes. No broad kill/reap even on assertion failure.
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            if info is None and info_path.exists():
                info = json.loads(info_path.read_text())
            if info is not None:
                state = process_table().get(info['pid'])
                if state is not None and state['starttime'] == info['starttime']:
                    fd = os.pidfd_open(info['pid'])
                    try: signal.pidfd_send_signal(fd, signal.SIGKILL)
                    finally: os.close(fd)
                    try: os.waitpid(info['pid'], 0)
                    except ChildProcessError: pass
            sentinel.terminate()
            sentinel.wait(timeout=5)
            result['testOwnedCleanupComplete'] = info is None or info['pid'] not in process_table()
            (evidence/'test-result.json').write_text(json.dumps(result, indent=2)+'\n')

    def test_clean_success(self):
        self.exercise('clean', 0, escalation=False)

    def test_normal_exit_with_term_ignoring_descendant(self):
        self.exercise('normal', 0)

    def test_failure_with_term_ignoring_descendant(self):
        self.exercise('failure', 1)

    def test_timeout_leader_term_exits_descendant_ignores(self):
        self.exercise('timeout', 1)

    def test_timeout_leader_and_descendant_ignore_term(self):
        self.exercise('ignore-all', 1)

    def test_repeated_sigterm_during_cleanup(self):
        self.exercise('cancel', 1, cancel=True)

    def test_exception_after_actual_fork(self):
        self.exercise('exception', 1, exception=True)

    def test_descendant_new_session(self):
        self.exercise('escape', 0)

    def test_orphan_zombie_reaped(self):
        self.exercise('zombie', 0, escalation=False)

    def test_cleanup_observation_error_cannot_report_pass(self):
        self.exercise('cleanup-exception', 1, exception=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
