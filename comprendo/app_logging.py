import logging
from contextvars import ContextVar

from opentelemetry import trace

from comprendo import __version__
from comprendo.server.security import ClientCredentials
from comprendo.types.task import Task

ctx_task: Task = ContextVar("task")
ctx_client: ClientCredentials | None = ContextVar("client")


class ContextFilter(logging.Filter):
    def filter(self, record):
        task: Task = ctx_task.get(None)
        client: ClientCredentials | None = ctx_client.get(None)
        if task is None:
            record.request_id = ""
            record.mock_mode = ""
        else:
            record.request_id = task.request.id
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
            "%(asctime)s %(levelname)s [%(name)s] {req=%(request_id)s,client=%(client_id)s,mock=%(mock_mode)s} - %(message)s"
        )
    )
    app_logger.addHandler(sh)


def set_logging_context(task: Task, client: ClientCredentials | None):
    current_span = trace.get_current_span()
    current_span.set_attribute("server.version", __version__)

    if task:
        ctx_task.set(task)
        current_span.set_attribute("request.id", task.request.id)
        current_span.set_attribute("mock_mode", task.mock_mode)
    if client:
        ctx_client.set(client)
        current_span.set_attribute("user.id", client.id)
