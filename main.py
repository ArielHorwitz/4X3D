from loguru import logger
from pathlib import Path
import arrow

logger.remove()
logfile = Path.cwd() / 'debug.log'
logfile.unlink()
logger.add(f'debug.log', format='{name} | {message}', rotation='1 MB')
logger.info(f'Logging at {arrow.get()}')


from gui.gui import App

r = App().run()
print(r)
