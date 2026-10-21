"""Linux-only ownership for the dedicated, single-child render supervisor.

Keep the unreaped session leader as a PGID/SID reservation. Adopt orphaned
children (including setsid escapees), signal individual identities via pidfds,
and reap only observed owned children. Never use waitpid(-1) or a host killall.
"""
import ctypes
import os
from pathlib import Path
import signal
import time


TERM_GRACE = 5.0
KILL_GRACE = 5.0


def enable_subreaper():
    if not hasattr(os, 'pidfd_open') or not hasattr(signal, 'pidfd_send_signal'):
        raise RuntimeError('Linux pidfd support required before launching Blender')
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER')


def process_table():
    table = {}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            fields = (entry/'stat').read_text().rsplit(')', 1)[1].split()
        except (FileNotFoundError, ProcessLookupError):
            continue
        table[int(entry.name)] = {
            'state': fields[0], 'ppid': int(fields[1]),
            'pgid': int(fields[2]), 'sid': int(fields[3]),
            'starttime': int(fields[19]),
        }
    return table


class OwnedTree:
    def __init__(self, child):
        self.child = child
        self.members = {}
        self.reaped = []
        self.leader_reaped = False

    def leader_exited(self):
        # Unlike Popen.poll(), this does not release the leader's PID/PGID/SID.
        return os.waitid(os.P_PID, self.child.pid,
                         os.WEXITED | os.WNOHANG | os.WNOWAIT) is not None

    def observe(self):
        table = process_table()
        owned = {pid for pid, state in table.items()
                 if state['sid'] == self.child.pid or state['ppid'] == os.getpid()}
        owned.update(pid for pid, member in self.members.items()
                     if pid in table and table[pid]['starttime'] == member['starttime'])
        # Also follow non-orphaned descendants which created another session.
        while True:
            extra = {pid for pid, state in table.items() if state['ppid'] in owned}
            if extra <= owned:
                break
            owned.update(extra)
        result = {}
        for pid in sorted(owned):
            state = table[pid]
            member = self.members.get(pid)
            if member is not None and member['starttime'] != state['starttime']:
                raise RuntimeError('owned PID identity changed')
            if member is None:
                try:
                    fd = os.pidfd_open(pid)
                except ProcessLookupError:
                    continue
                # Verify the identity again after acquiring the non-reusable handle.
                current = process_table().get(pid)
                if current is None or current['starttime'] != state['starttime']:
                    os.close(fd)
                    continue
                member = dict(state, pid=pid, pidfd=fd)
                self.members[pid] = member
            result[pid] = state
        return result

    def send(self, signum, observed):
        # The leader remains unreaped throughout cleanup. Its private session
        # cannot be joined by unrelated host processes or reused for a new PGID.
        try:
            os.killpg(self.child.pid, signum)
        except ProcessLookupError:
            pass
        for pid, state in observed.items():
            if state['state'] == 'Z':
                continue
            try:
                signal.pidfd_send_signal(self.members[pid]['pidfd'], signum)
            except ProcessLookupError:
                pass

    def reap_descendants(self, observed):
        for pid, state in observed.items():
            if pid == self.child.pid or state['ppid'] != os.getpid():
                continue
            try:
                reaped, status = os.waitpid(pid, os.WNOHANG)
            except ChildProcessError:
                continue
            if reaped:
                self.reaped.append({'pid': pid, 'status': status})

    def cleanup(self, record, persist):
        """Bounded TERM then KILL; never release the lock on unconfirmed cleanup.

        An unkillable/D-state child or observation failure keeps the supervisor
        alive holding heavy1, with FAIL evidence. SIGINT/TERM handlers in the
        caller only record cancellation, so repeated cancellation cannot escape.
        SIGKILL/host failure cannot be defended by any userspace finally block.
        """
        record['cleanup'] = {'termGraceSeconds': TERM_GRACE,
                             'killGraceSeconds': KILL_GRACE,
                             'killEscalated': False, 'confirmed': False}
        started = time.monotonic()
        sent_term = False
        while True:
            try:
                observed = self.observe()
                self.reap_descendants(observed)
                # A zombie leader must stay pinned until every descendant has
                # gone, including zombies adopted and reaped by this subreaper.
                observed = self.observe()
                if self.leader_exited() and set(observed) <= {self.child.pid}:
                    self.child.wait()
                    self.leader_reaped = True
                    try:
                        os.killpg(self.child.pid, 0)
                    except ProcessLookupError:
                        record['ownedGroupGone'] = True
                        record['ownedTreeGone'] = True
                        record['cleanup']['confirmed'] = True
                        break
                    raise RuntimeError('group present after final leader reap')
                elapsed = time.monotonic() - started
                if not sent_term:
                    self.send(signal.SIGTERM, observed)
                    sent_term = True
                elif elapsed >= TERM_GRACE:
                    self.send(signal.SIGKILL, observed)
                    record['cleanup']['killEscalated'] = True
                if elapsed >= TERM_GRACE + KILL_GRACE:
                    record['status'] = 'FAIL'
                    record['cleanup']['error'] = 'cleanup deadline exceeded; retaining heavy1'
                    record['ownedGroupGone'] = False
                    persist()
            except Exception as exc:
                record['status'] = 'FAIL'
                record['cleanup']['error'] = f'{type(exc).__name__}: {exc}; retaining heavy1'
                record['ownedGroupGone'] = False
                persist()
            time.sleep(.05)
        record['cleanup']['elapsedSeconds'] = time.monotonic() - started
        record['cleanup']['members'] = [
            {k: v for k, v in member.items() if k != 'pidfd'}
            for member in self.members.values()]
        record['cleanup']['reapedDescendants'] = self.reaped
        for member in self.members.values():
            os.close(member['pidfd'])
