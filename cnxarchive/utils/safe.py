import subprocess
import threading

from subprocess import PIPE
from logging import getLogger

logger = getLogger('safestat')

safe_stat_process = None


def safe_stat(path, timeout=1, cmd=None):
    "Use threads and a subproc to bodge a timeout on top of filesystem access"
    global safe_stat_process

    if cmd is None:
        cmd = ['/usr/bin/stat']

    cmd.append(path)

    def target():
        global safe_stat_process
        logger.debug('Stat thread started')
        safe_stat_process = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE)
        _results = safe_stat_process.communicate()  # noqa
        logger.debug('Stat thread finished')

    thread = threading.Thread(target=target)
    thread.start()

    thread.join(timeout)

    if thread.is_alive():  # stat took longer than timeout
        safe_stat_process.terminate()
        thread.join()
    return safe_stat_process.returncode == 0
