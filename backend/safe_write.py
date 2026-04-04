"""Atomic file-write helpers.

Provides utilities that write to a temporary file in the same directory
and then atomically replace the target, preventing corruption from
crashes or concurrent writes.

``os.replace()`` is atomic on POSIX when source and destination are on
the same filesystem (guaranteed here because the temp file is created
in the same directory).  On Windows it is not strictly atomic, but it
*is* an overwrite (no "delete then rename" race) and is the best
available primitive.
"""

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, IO


@contextmanager
def atomic_write(target: str | Path, mode: str = "w", **open_kwargs) -> Iterator[IO]:
    """Context manager that writes to *target* atomically.

    Usage::

        with atomic_write("/data/config.json") as f:
            json.dump(data, f, indent=2)

    The file is first written to a temporary file in the same directory.
    When the context exits cleanly the temp file is flushed, fsynced, and
    atomically renamed over *target*.  If an exception is raised the temp
    file is removed and the original is left untouched.
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd = tempfile.NamedTemporaryFile(
        mode=mode,
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        delete=False,
        **open_kwargs,
    )
    try:
        yield fd
        fd.flush()
        os.fsync(fd.fileno())
        fd.close()
        os.replace(fd.name, target)
    except BaseException:
        fd.close()
        try:
            os.unlink(fd.name)
        except OSError:
            pass
        raise


def atomic_write_bytes(target: str | Path, data: bytes) -> None:
    """Write *data* to *target* atomically."""
    with atomic_write(target, mode="wb") as f:
        f.write(data)
