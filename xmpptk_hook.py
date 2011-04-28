import logging
from subprocess import Popen

log = logging.getLogger('xmpptk-make')

def preconfigure(options, buildout, environment):
    proc = Popen(
      "git submodule update --init".split(" "),
      cwd=buildout['xmpptk']['location']
    )

    (stdoutdata, stderrdata) = proc.communicate()

    if stderrdata:
        log.error(stderrdata)

    log.info(stdoutdata)

