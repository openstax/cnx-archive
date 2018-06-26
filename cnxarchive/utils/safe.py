import subprocess
import threading

from subprocess import PIPE
from logging import getLogger

logger = getLogger('safestat')

process = None


def safe_stat(path, timeout=1, cmd=None):
    "Use threads and a subproc to bodge a timeout on top of filesystem access"
    global process

    if cmd is None:
        cmd = ['/usr/bin/stat']

    cmd.append(path)

    # import pdb; pdb.set_trace()
    def target():
        global process
        logger.debug('Stat thread started')
        process = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE)
        _results = process.communicate()  # noqa
        logger.debug('Stat thread finished')

    thread = threading.Thread(target=target)
    thread.start()

    thread.join(timeout)

    if thread.is_alive():  # stat took longer than timeout
        process.terminate()
        thread.join()
    return process.returncode == 0
