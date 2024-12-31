import hashlib
import os
import pathlib
import shutil


class SimpleFileCache:
    def __init__(self, cache_dir: str, context: list[str]):
        self.cache_dir = pathlib.Path(cache_dir)
        self.context_hash = self._generate_hash_from_inputs(context)
        self.context_hash_filename = f"{self.context_hash}.ctx.hash"

        if not (self.cache_dir / self.context_hash_filename).exists():
            # different hash or no cache - remove the cache folder and recreate
            shutil.rmtree(self.cache_dir, ignore_errors=True)
            os.makedirs(self.cache_dir, exist_ok=True)

            # touch the cache hash file - this cache folder is not hashed to this input set
            pathlib.Path(self.cache_dir / self.context_hash_filename).touch()

    def _generate_hash_from_inputs(self, context_strs: list[str]):
        # concat in order and return the digest MD5
        all_context = "".join(context_strs)
        return hashlib.md5(all_context.encode()).hexdigest()

    def _get_content_filename(self, key: str) -> str:
        return f"{key}.content"

    def get(self, key: str) -> str:
        cached_content_filename = self._get_content_filename(key)
        if pathlib.Path(self.cache_dir / cached_content_filename).exists():
            with open(self.cache_dir / cached_content_filename, "r") as f:
                return f.read()
        return None

    def put(self, key: str, content: str) -> None:
        with open(self.cache_dir / self._get_content_filename(key), "w") as f:
            f.write(content)
