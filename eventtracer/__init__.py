#!/usr/bin/env python3

from io import SEEK_END
from os import getpid
import typing as t
import json
from time import time
import threading
import sys
from contextlib import contextmanager

Name = t.Optional[str]
Args = t.Optional[t.Dict[str, t.Any]]
Cat = t.Optional[str]
Id = t.Optional[str]
Scope = t.Optional[str]


class EventTracer:
    def __init__(self, filename: t.Optional[str] = None):
        """
        Create a new EventTracer object. If $filename is specified, events
        will be written to that file in realtime. If not, they will be buffered
        for the lifetime of the object, and they can be written to a file later
        in one go with flush($filename)
        """
        self.buffer: t.Optional[t.List[t.Dict[str, t.Any]]] = None
        self.fp: t.Optional[t.Any] = None
        self.depths: t.Dict[int, int] = {}

        if filename:
            self.fp = open(filename, "a")
            self.fp.seek(0, SEEK_END)
            if self.fp.tell() == 0:
                self.fp.write("[\n")
                self.fp.flush()
        else:
            self.buffer = []

    def __del__(self):
        if self.fp:
            self.fp.close()

    def __str__(self):
        return "\n".join(repr(x) for x in self.buffer)

    #
    # Meta-methods
    #
    def clear(self):
        p = getpid()
        if p not in self.depths:
            return

        while self.depths[p] > 0:
            self.end()

    def flush(self, filename: str):
        if self.buffer is None:
            raise Exception("Called flush() on an unbuffered stream")

        encoded = json.dumps(self.buffer)
        self.buffer = []

        with open(filename, "a") as fp:
            # FIXME: if(flock(fp, LOCK_EX)):
            fp.seek(0, SEEK_END)
            if fp.tell() != 0:
                encoded = encoded[1:]
            encoded = encoded[:-1] + ",\n"
            fp.write(encoded)
            fp.flush()
            # FIXME: flock(fp, LOCK_UN)

    def _log_event(self, ph: str, optionals: t.Dict[str, t.Any]):
        d = {
            "ph": ph,
            "ts": int(time() * 1000000),
            "pid": getpid(),
            "tid": threading.get_ident(),
        }
        for k, v in optionals.items():
            if v is not None:
                d[k] = v

        if self.fp:
            self.fp.write(json.dumps(d) + ",\n")
            self.fp.flush()
        else:
            self.buffer.append(d)

    #
    # Methods which map ~1:1 with the specification
    #

    def begin(self, name: str, args: Args = None, cat: Cat = None):
        self._log_event("B", {"name": name, "cat": cat, "args": args})
        if getpid() not in self.depths:
            self.depths[getpid()] = 0
        self.depths[getpid()] += 1

    def end(self, name: Name = None, args: Args = None, cat: Cat = None):
        self._log_event("E", {"name": name, "cat": cat, "args": args})
        self.depths[getpid()] -= 1

    def complete(
        self,
        start: float,
        duration: float,
        name: Name = None,
        args: Args = None,
        cat: Cat = None,
    ):
        self._log_event(
            "X", {"ts": start, "dur": duration, "name": name, "cat": cat, "args": args}
        )

    def instant(
        self, name: Name = None, scope: Scope = None, args: Args = None, cat: Cat = None
    ):
        # assert($scope in [g, p, t])
        self._log_event("I", {"name": name, "cat": cat, "scope": scope, "args": args})

    def counter(self, name: Name = None, args: Args = None, cat: Cat = None):
        self._log_event("C", {"name": name, "cat": cat, "args": args})

    def async_start(
        self, name: Name = None, id: Id = None, args: Args = None, cat: Cat = None
    ):
        self._log_event("b", {"name": name, "id": id, "cat": cat, "args": args})

    def async_instant(
        self, name: Name = None, id: Id = None, args: Args = None, cat: Cat = None
    ):
        self._log_event("n", {"name": name, "id": id, "cat": cat, "args": args})

    def async_end(
        self, name: Name = None, id: Id = None, args: Args = None, cat: Cat = None
    ):
        self._log_event("e", {"name": name, "id": id, "cat": cat, "args": args})

    def flow_start(
        self, name: Name = None, id: Id = None, args: Args = None, cat: Cat = None
    ):
        self._log_event("s", {"name": name, "id": id, "cat": cat, "args": args})

    def flow_instant(
        self, name: Name = None, id: Id = None, args: Args = None, cat: Cat = None
    ):
        self._log_event("t", {"name": name, "id": id, "cat": cat, "args": args})

    def flow_end(
        self, name: Name = None, id: Id = None, args: Args = None, cat: Cat = None
    ):
        self._log_event("f", {"name": name, "id": id, "cat": cat, "args": args})

    # deprecated
    # def sample():P}

    def object_created(
        self,
        name: Name = None,
        id: Id = None,
        args: Args = None,
        cat: Cat = None,
        scope: Scope = None,
    ):
        self._log_event(
            "N", {"name": name, "id": id, "cat": cat, "args": args, "scope": scope}
        )

    def object_snapshot(
        self,
        name: Name = None,
        id: Id = None,
        args: Args = None,
        cat: Cat = None,
        scope: Scope = None,
    ):
        self._log_event(
            "O", {"name": name, "id": id, "cat": cat, "args": args, "scope": scope}
        )

    def object_destroyed(
        self,
        name: Name = None,
        id: Id = None,
        args: Args = None,
        cat: Cat = None,
        scope: Scope = None,
    ):
        self._log_event(
            "D", {"name": name, "id": id, "cat": cat, "args": args, "scope": scope}
        )

    def metadata(self, name: Name = None, args: Args = None):
        self._log_event("M", {"name": name, "args": args})

    # "The precise format of the global and process arguments has not been determined yet"
    # def memory_dump_global():V}
    # def memory_dump_process():v}

    def mark(self, name: Name = None, args: Args = None, cat: Cat = None):
        self._log_event("R", {"name": name, "cat": cat, "args": args})

    def clock_sync(
        self, name: Name = None, sync_id: Id = None, issue_ts: t.Optional[float] = None
    ):
        self._log_event(
            "c", {"name": name, "args": {"sync_id": sync_id, "issue_ts": issue_ts}}
        )

    def context_enter(self, name: Name = None, id: Id = None):
        self._log_event("(", {"name": name, "id": id})

    def context_leave(self, name: Name = None, id: Id = None):
        self._log_event(")", {"name": name, "id": id})

    #
    # Language-specific bits
    #

    def _profile(self, frame, action, params):
        if action == "call":
            self.begin(
                frame.f_code.co_name,
                {
                    "filename": frame.f_code.co_filename,
                    "lineno": frame.f_code.co_firstlineno,
                },
            )
        if action == "return":
            self.end()

    def set_profile(self, active: bool=False):
        if active:
            self.begin("Profiling init")
            sys.setprofile(self._profile)
        else:
            sys.setprofile(None)
            self.end("Profiling exit")

    @contextmanager
    def context(self, name: Name):
        self.begin(name)
        yield
        self.end()

    def decorator(self, func):
        def inner(*args, **kwargs):
            self.begin(func.__code__.co_name)
            r = func(*args, **kwargs)
            self.end()
            return r

        return inner
