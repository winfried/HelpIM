import logging
from subprocess import check_output

log = logging.getLogger('xmpptk-make')

def preconfigure(options, buildout, environment):
    log.info(check_output(
      "git submodule update --init".split(" "),
      cwd=buildout['xmpptk']['location']
    ))

