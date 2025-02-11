import pathlib

from comprendo.types.task import Task


base_cache_dir = pathlib.Path("extraction_cache")


def get_namespace_cache_dir(task: Task, namespace: str) -> pathlib.Path:
    return base_cache_dir / task.request.id / namespace
