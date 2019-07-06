from dataclasses import dataclass
from typing import Any, Callable
from threading import Event
from queue import Queue
from time import time

@dataclass
class Holder:
    data: Any

@dataclass
class Remainder:
    stop: Holder
    left: Holder


@dataclass
class Resource:
    invalid_after: float
    data: Any

    def __bool__(self):
        return time() <= self.invalid_after


@dataclass
class Request:
    event: Event
    resource: Resource


def storable(Qstored: Queue, func, stop: Remainder, thence):
    while not stop.stop.data:
        item = func()
        if item is not None:
            Qstored.put(item)
    stop.left.data -= 1
    thence()


def unstorable(Qrequest: Queue, func: Callable[[], Resource], stop: Remainder, thence):
    while not stop.stop.data:
        r: Request = Qrequest.get()
        r.resource = func()
        r.event.set()
        Qrequest.task_done()
    stop.left.data -= 1
    thence()


def process(Qrequest: Queue, Qstored: Queue, func: Callable[[Any, Any], Any], Qresult: Queue, stop: Remainder, thence):
    r = Request(Event(), Resource(0, "0.0.0.0:0"))
    while not stop.stop.data or not Qstored.empty():
        s = Qstored.get()
        if not r.resource:
            r.event.clear()
            Qrequest.put(r)
            r.event.wait()
        Qresult.put(func(r.resource.data, s))
        Qstored.task_done()
    stop.left.data -= 1
    thence()
