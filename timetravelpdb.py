import os
import pdb
import pprint
import signal
import time


def dlog(message: str) -> None:
    print(message)


class TimeTravelPdb(pdb.Pdb):
    def __init__(
        self, completekey="tab", stdin=None, stdout=None, skip=None, nosigint=False, readrc=True
    ) -> None:
        self._tomography_enabled = True  # Is snapshoting enabled.
        self._tomography_pids = []  # List of snapshot pids, newest at the end.
        self._tomography_id_of = {}  # pid -> serial number translation.
        self._tomography_pid_of = {}  # Serial number -> pid translation.
        self._tomography_descriptions = {}  # Serial -> human-readable description
        self._tomography_serial = 0  # How many snapshots taken so far.
        self._tomography_child = False  # Are we in a child process.
        self.umax = 100  # Max tomographic copies to retain
        super().__init__(completekey, stdin, stdout, skip, nosigint, readrc)

    def do_quit(self, arg: str) -> bool | None:
        self._tom_quit()
        return super().do_quit(arg)

    def do_EOF(self, arg: str) -> bool | None:
        self._tom_quit()
        return super().do_EOF(arg)

    def interaction(self, frame, traceback) -> None:
        if self._tomography_enabled:
            self._tomography_snapshot(frame)
        return super().interaction(frame, traceback)

    def set_tomography_on(self):
        self._tomography_enabled = True

    def set_tomography(self):
        self._tomography_enabled = False

    def _tomography_snapshot(self, frame):
        def _handle_cont(self, foo):
            dlog("CONTINUE")
            pass

        def _handle_int(self, foo):
            dlog("INT")
            os._exit(0)
            pass

        dlog("SNAP")
        pid = os.fork()
        if pid:
            # Parent:
            self._tomography_pids.append(pid)
            num = self._tomography_serial = self._tomography_serial + 1
            self._tomography_id_of[pid] = num
            self._tomography_pid_of[num] = pid
            self.prompt = f"(Pdb:{num - 1}) "
            t = time.localtime()
            desc = ('%s:%s' % (self.canonic(frame.f_code.co_filename), frame.f_lineno))[-75:]
            self._tomography_descriptions[num] = f"{num - 1}: {pid} [{t[3]}:{t[4]}:{t[5]}] {desc}"
        else:
            # Child
            self._tomography_child = True
            dlog("CHILD SLEEPING")
            signal.signal(signal.SIGCONT, _handle_cont)
            signal.signal(signal.SIGINT, _handle_int)
            signal.pause()
            signal.signal(signal.SIGINT, signal.default_int_handler)
            dlog("CHILD WAKING UP")
            num = self._tomography_serial = self._tomography_serial + 1  # Skip ourself
            self.prompt = f"(Pdb:{num - 1}) "
            return
        dlog("PIDS = %s" % self._tomography_pids)
        while len(self._tomography_pids) > self.umax:
            victim = self._tomography_pids[0]
            del self._tomography_pids[0]  # Forget it
            self._forget_pid(victim)
            os.kill(victim, signal.SIGTERM)  # Kill it.
            dlog(f"KILLED {victim}")

    def _forget_pid(self, pid):
        serial = self._tomography_id_of[pid]
        del self._tomography_id_of[pid]
        del self._tomography_pid_of[serial]
        del self._tomography_descriptions[serial]

    def _tom_quit(self):
        dlog(f"self._tomography_child = {self._tomography_child}")
        if self._tomography_child:
            dlog("THE CHILD, NO SNAPSHOT KILLING")
            return
        dlog("KILLING SNAPSHOTS")
        for victim in self._tomography_pids:
            os.kill(victim, signal.SIGTERM)  # Kill it.
        self._tomography_pids = []
        self._tomography_descriptions = {}
        self._tomography_ids = {}

    def do_tom(self, arg):
        self._tomography_enabled = not self._tomography_enabled
        if self._tomography_enabled:
            print("TOM ON")
        else:
            print("TOM OFF")

    def do_uup(self, arg):
        def _continue(self, foo):
            dlog("UP DONE ; CONTINUE")

        dlog("CHILD TELLING PARENT TO CONTINUE")
        signal.signal(signal.SIGCONT, _continue)
        os.kill(os.getppid(), signal.SIGCONT)
        signal.pause()

    def do_tomoff(self, arg):
        print("TOM OFF")
        self._tomography_enabled = False

    def do_ulist(self, arg):
        for pid in self._tomography_pids:
            print(self._tomography_descriptions[self._tomography_id_of[pid]])

    def do_ujump(self, arg):

        def _handle_cont(self, foo):
            dlog("UJUMP DONE (CHILD POPPED). CONTINUE")

        def _handle_child(self, foo):
            dlog("UJUMP DONE (CHILD DIED). CONTINUE")
            dlog(f"WAITPID({pid})")
            try:
                retcode = os.waitpid(pid, 0)
            except OSError:
                dlog(f"No such child: {pid}")
                return
            dlog(f"WAIT RET = {retcode}")

        try:
            dlog("PIDS:")
            dlog(pprint.pformat(self._tomography_pids))
            dlog(pprint.pformat(self._tomography_descriptions))
            dlog(pprint.pformat(self._tomography_pid_of))
            pid = self._tomography_pid_of[int(arg) + 1]
        except (IndexError, KeyError, ValueError):
            print(f"ERR: No such universe: {arg}")
            return
        # Tell the child to go, and we pause.
        dlog(f"VIVIFY {pid}")
        signal.signal(signal.SIGCHLD, _handle_child)
        signal.signal(signal.SIGCONT, _handle_cont)
        os.kill(pid, signal.SIGCONT)
        dlog("PAUSING")
        signal.pause()
        dlog("CHILD GONE. PARENT CONTINUES")
        # We've returned. Let's make sure all the PIDs are good.
        for i, pid in reversed(list(enumerate(self._tomography_pids))):
            try:
                os.kill(pid, 0)
                dlog(f"PID ALIVE {pid}")
            except OSError:
                dlog(f"PID DEAD {pid}")
                del self._tomography_pids[i]  # Forget it
                self._forget_pid(pid)

    def help_ulist(self):
        print("""ulist View the list of universes saved in the multiverse.""")
