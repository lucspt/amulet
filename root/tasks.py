from multiprocessing import Process, Queue
from typing import Any, Callable, Iterable


class Task:
    __slots__ = ("task", "applied", "_task", "signature")

    def __init__(self, task: Callable):
        self._task = task
        self.task = self.add_queue(func=task)
        self.applied = False
        self.signature = False, (), {}

    def add_queue(self, func: Callable) -> Callable:
        """wraps a function and puts it's result in a queue for retrieval"""
        self.queue = Queue()

        def q_wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            self.queue.put(res or None)

        return q_wrapper

    def apply_async(self, *args, **kwargs) -> None:
        """starts a process with given args, kwargs and
        possibly previously signed arguments
        """
        signature = self.signature
        if signature[0]:
            args += signature[1]
            kwargs = {**kwargs, **signature[-1]}
        p = Process(target=self.task, args=args, kwargs=kwargs)
        self.process = p
        p.start()
        self.applied = True
        self.signature = False, (), {}

    def s(self, *args, **kwargs) -> Any:
        """attatches arguments to self for when called"""
        self.signature = True, args, kwargs
        self.applied = False
        self.add_queue(func=self._task)
        return self

    def get(self, *args, **kwargs) -> Any:
        """join the processs and return its result from the queue"""
        if not self.applied:
            self.apply_async(*args, **kwargs)
        self.applied = False
        q_res = self.queue.get()
        self.process.join()
        return q_res

    def __call__(self, *args, **kwargs):
        return self.get(*args, **kwargs)


class Parallelization:
    def task(self, func) -> Task:
        return Task(task=func)

    def in_parallel(self, tasks: tuple[Task]) -> Task:
        """Gets tasks ready to be run in parallel"""

        def _parallel():
            [task.apply_async() for task in tasks]
            res = tuple(task.get() for task in tasks)
            if len(res) == 1:
                res = res[0]
            return res

        return Task(task=_parallel)

    def chain(self, tasks: Iterable[Callable]) -> Task:
        """Get's tasks ready to be run sequentially,
        using the return values of each one for the next"""

        def _chain():
            res = tasks[0].get()
            res = tuple(task.get(res) for task in tasks[1:])
            if len(res) == 1:
                res = res[0]
            return res

        return Task(task=_chain)

    def group(self, group: tuple[Task]) -> tuple:
        """Runs a group of tasks in parallel"""
        [g.apply_async() for g in group]
        return tuple(g.get() for g in group)
