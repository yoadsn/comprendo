import logging
from contextvars import ContextVar

from comprendo.types.task import Task
from comprendo.server.security import ClientCredentials

ctx_task: Task = ContextVar("task")
ctx_client: ClientCredentials | None = ContextVar("client")


class ContextFilter(logging.Filter):
    def filter(self, record):
        task: Task = ctx_task.get(None)
        client: ClientCredentials | None = ctx_client.get(None)
        if task is None:
            record.requestid = ""
            record.mock_mode = ""
        else:
            record.requestid = task.request.id
            record.mock_mode = task.mock_mode

        if client is None:
            record.client_id = ""
        else:
            record.client_id = client.id

        return True


def init_logging(app_name):
    app_logger = logging.getLogger(app_name)
    app_logger.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.addFilter(ContextFilter())
    sh.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] {req=%(requestid)s,client=%(client_id)s,mock=%(mock_mode)s} - %(message)s"
        )
    )
    app_logger.addHandler(sh)


def set_logging_context(task: Task, client: ClientCredentials | None):
    if task:
        ctx_task.set(task)
    if client:
        ctx_client.set(client)
