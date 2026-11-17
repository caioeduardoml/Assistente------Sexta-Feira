"""Gerenciador de trava de instancia unica (PID Lock) com deteccao de PID obsoleto."""

import os


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class PidLock:
    """Garante que apenas uma instancia do processo esteja ativa."""

    def __init__(self, pid_file: str) -> None:
        self.pid_file = pid_file
        self._acquired = False

    def acquire(self) -> bool:
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, "r", encoding="utf-8") as f:
                    old_pid = int(f.read().strip())
                if _pid_exists(old_pid):
                    return False
            except (ValueError, OSError):
                pass
            # Remove arquivo PID obsoleto de execucao anterior
            try:
                os.remove(self.pid_file)
            except OSError:
                return False

        with open(self.pid_file, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        self._acquired = True
        return True

    def release(self) -> None:
        if not self._acquired:
            return
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
        except OSError:
            pass
        self._acquired = False

    def __enter__(self) -> "PidLock":
        if not self.acquire():
            raise RuntimeError(f"Outra instancia ja esta ativa ({self.pid_file}).")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
