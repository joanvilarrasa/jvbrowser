import threading

class Task:
    def __init__(self, task_code, *args):
        self.task_code = task_code
        self.args = args

    def run(self):
        self.task_code(*self.args)
        self.task_code = None
        self.args = None


class TaskRunner:
    def __init__(self, tab):
        self.tab = tab
        self.tasks = []
        self._lock = threading.Lock()

    def schedule_task(self, task):
        # Tasks may be scheduled from other threads (e.g., timers/XHR)
        with self._lock:
            self.tasks.append(task)

    def run(self):
        # Non-blocking: run at most one task if available
        task = None
        with self._lock:
            if self.tasks:
                task = self.tasks.pop(0)
        if task:
            task.run()