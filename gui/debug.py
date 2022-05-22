
import arrow
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import HTML

from gui import window_size



class Debug(Window):
    def __init__(self, app):
        self.text_control = FormattedTextControl(text='Debug')
        super().__init__(content=self.text_control, always_hide_cursor=True)
        self.app = app

    def update(self):
        t = arrow.get().format('YY-MM-DD, hh:mm:ss')
        self.text_control.text = HTML('\n'.join([
            f'<h1>SIM</h1>',
            f'<red>Auto sim</red>: <code>{self.app.auto_sim}</code>',
            f'<red>Tick</red>: <code>{self.app.universe.tick}</code>',
            f'<h2>POS</h2>',
            f'{self.app.universe.positions[:10]}',
            f'<h2>VEL</h2>',
            f'{self.app.universe.velocities[:10]}',
        ]))
