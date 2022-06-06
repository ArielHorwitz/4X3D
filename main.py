from loguru import logger
from pathlib import Path
import arrow

logger.remove()
logfile = Path.cwd() / 'debug.log'
if logfile.is_file():
    logfile.unlink()
logger.add(logfile, rotation='5 MB', retention=2,
    format='{level};{name}:{line}:: {message}')
logger.info(f'Logging at {arrow.get()}')


from gui.gui import App

r = App().run()
print(r)
