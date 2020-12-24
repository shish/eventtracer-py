#!/usr/bin/env python3

from eventtracer import EventTracer
from time import time, sleep
import unittest
import os.path
import json


def nanotime():
    return int(time() * 1000000)

def minisleep():
    sleep(0.1)

out = ""


def hello(et: EventTracer) -> None:
    global out
    et.begin("saying hello")
    out += "hello "
    minisleep()
    et.end()


def greet(et: EventTracer, name: str) -> None:
    global out
    et.complete(nanotime(), 200000, f"greeting {name}")
    out += f"{name}\n"
    sleep(2)


class EventTracerTest(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.tmpfile = "trace.json"
        if os.path.exists(self.tmpfile):
            os.unlink(self.tmpfile)

    def tearDown(self) -> None:
        super().tearDown()
        if os.path.exists(self.tmpfile):
            os.unlink(self.tmpfile)

    def assertArraySubset(self, small, big) -> None:
        for k, v in small.items():
            self.assertEqual(big[k], v)

    #
    # Test the main logging methods
    #
    def testEmpty(self) -> None:
        et = EventTracer()
        self.assertEqual(0, len(et.buffer))

    def testBeginEnd(self) -> None:
        et = EventTracer()
        et.begin("running program")
        et.end()
        self.assertEqual(2, len(et.buffer))
        self.assertArraySubset({"ph": "B", "name": "running program"}, et.buffer[0])
        self.assertArraySubset({"ph": "E"}, et.buffer[1])

    def testComplete(self) -> None:
        et = EventTracer()
        et.complete(nanotime(), 1000000, "complete item")
        self.assertEqual(1, len(et.buffer))
        self.assertArraySubset({"ph": "X", "name": "complete item"}, et.buffer[0])

    def testNesting(self) -> None:
        et = EventTracer()
        et.begin("running program")
        hello(et)
        greet(et, "world")
        et.end()
        self.assertEqual(5, len(et.buffer))
        self.assertArraySubset({"ph": "B", "name": "running program"}, et.buffer[0])
        self.assertArraySubset({"ph": "E"}, et.buffer[4])

    def testInstant(self) -> None:
        et = EventTracer()
        et.instant("Test Begins", "p")
        et.begin("running program")
        et.end()
        self.assertEqual(3, len(et.buffer))
        self.assertArraySubset({"ph": "I", "name": "Test Begins"}, et.buffer[0])

    def testCounter(self) -> None:
        et = EventTracer()
        et.counter("cache", {"hits": 0, "misses": 0})
        minisleep()
        et.counter("cache", {"hits": 1, "misses": 0})
        minisleep()
        et.counter("cache", {"hits": 1, "misses": 1})
        self.assertEqual(3, len(et.buffer))
        self.assertArraySubset({"ph": "C", "name": "cache"}, et.buffer[0])

    def testAsync(self) -> None:
        et = EventTracer()
        et.async_start("start", "my_id")
        minisleep()
        et.async_instant("instant", "my_id")
        minisleep()
        et.async_end("end", "my_id")
        self.assertEqual(3, len(et.buffer))
        self.assertArraySubset({"ph": "b", "name": "start"}, et.buffer[0])

    def testFlow(self) -> None:
        et = EventTracer()
        et.flow_start("start", "my_id")
        minisleep()
        et.flow_instant("instant", "my_id")
        minisleep()
        et.flow_end("end", "my_id")
        self.assertEqual(3, len(et.buffer))
        self.assertArraySubset({"ph": "s", "name": "start"}, et.buffer[0])

    def testObject(self) -> None:
        et = EventTracer()
        et.object_created("my_ob", "my_id")
        minisleep()
        et.object_snapshot("my_ob", "my_id")
        minisleep()
        et.object_destroyed("my_ob", "my_id")
        self.assertEqual(3, len(et.buffer))
        self.assertArraySubset({"ph": "N", "name": "my_ob"}, et.buffer[0])

    def testMetadata(self) -> None:
        et = EventTracer()
        et.metadata("process_name", {"name": "my_process_name"})
        et.metadata("process_labels", {"labels": "my_process_label"})
        et.metadata("process_sort_index", {"sort_index": 0})
        et.metadata("thread_name", {"name": "my_thread_name"})
        et.metadata("thread_sort_index", {"sort_index": 0})
        self.assertEqual(5, len(et.buffer))
        self.assertArraySubset({"ph": "M", "name": "process_name"}, et.buffer[0])

    def testMark(self) -> None:
        et = EventTracer()
        et.mark("my_mark")
        self.assertEqual(1, len(et.buffer))
        self.assertArraySubset({"ph": "R", "name": "my_mark"}, et.buffer[0])

    def testClockSync(self) -> None:
        et = EventTracer()
        et.clock_sync("sync", "sync_id", None)
        et.clock_sync("sync", "sync_id", 12345)
        self.assertEqual(2, len(et.buffer))
        self.assertArraySubset({"ph": "c", "name": "sync"}, et.buffer[0])

    def testContext(self) -> None:
        et = EventTracer()
        et.context_enter("context", "context_id")
        et.context_leave("context", "context_id")
        self.assertEqual(2, len(et.buffer))
        self.assertArraySubset({"ph": "(", "name": "context"}, et.buffer[0])

    #
    # I/O error situations
    #
    def testFlushUnbuffered(self) -> None:
        try:
            et = EventTracer(self.tmpfile)
            et.flush(self.tmpfile)
            self.assertTrue(False)
        except Exception as e:
            self.assertTrue(True)

    #
    # Utility things
    #
    def testEndOutstanding(self) -> None:
        et = EventTracer()
        et.clear()
        # clearing an un-used thread shouldn't crash

        et.begin("a")
        et.begin("b")
        et.begin("c")
        self.assertEqual(3, len(et.buffer))

        et.clear()
        self.assertEqual(6, len(et.buffer))

        et.flush(self.tmpfile)
        self.assertEqual(0, len(et.buffer))

    def testStreamingWrites(self) -> None:
        # Write two streams and make sure there's only one beginning
        et1 = EventTracer(self.tmpfile)
        et2 = EventTracer(self.tmpfile)
        et1.complete(nanotime(), 1, "item 1")
        et2.complete(nanotime(), 1, "item 2")

        # finished_data = data, minus trailing comma, plus closing brace
        with open(self.tmpfile) as fp:
            data = fp.read()
        finished_data = data[:-2] + "\n]"

        try:
            buffer = json.loads(finished_data)
            self.assertEqual(2, len(buffer))
        except Exception as e:
            print(finished_data)
            raise

    def testFlushingWrites(self) -> None:
        # Write two streams and make sure there's only one beginning
        et1 = EventTracer()
        et2 = EventTracer()
        et1.complete(nanotime(), 1, "flushed 1")
        et2.complete(nanotime(), 1, "flushed 2")
        et1.flush(self.tmpfile)
        et2.flush(self.tmpfile)

        # finished_data = data, minus trailing comma, plus closing brace
        with open(self.tmpfile) as fp:
            data = fp.read()
        finished_data = data[:-2] + "\n]"

        buffer = json.loads(finished_data)
        self.assertEqual(2, len(buffer))

    #
    # Test language-specific bits
    #
    def testContext(self):
        et = EventTracer()
        with et.context("outer context"):
            with et.context("inner context"):
                minisleep()
        self.assertEqual(4, len(et.buffer), et)

    def testDecorator(self):
        et = EventTracer()

        @et.decorator
        def method():
            minisleep()

        method()

        self.assertEqual(2, len(et.buffer), et)

    def testProfile(self):
        et = EventTracer()
        et.set_profile(True)

        def method():
            minisleep()

        method()
        et.set_profile(False)

        self.assertEqual(8, len(et.buffer), et)


if __name__ == "__main__":
    unittest.main()
