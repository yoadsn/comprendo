import logging
from contextvars import ContextVar

from comprendo.types.task import Task

ctx_task: Task = ContextVar("task")


class ContextFilter(logging.Filter):
    def filter(self, record):
        task: Task = ctx_task.get(None)
        if task is None:
            record.requestid = ""
            record.mock_mode = ""
        else:
            record.requestid = task.request.id
            record.mock_mode = task.mock_mode
        return True


def init_logging(app_name):
    app_logger = logging.getLogger(app_name)
    app_logger.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.addFilter(ContextFilter())
    sh.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] {req=%(requestid)s,mock=%(mock_mode)s} - %(message)s")
    )
    app_logger.addHandler(sh)


def set_logging_context(task: Task):
    ctx_task.set(task)
