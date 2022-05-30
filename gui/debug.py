
import numpy as np
import arrow
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import HTML

from gui import window_size, format_latlong, format_vector
from logic.universe import CELESTIAL_NAMES
from logic.quaternion import Quaternion as Quat


class Debug(Window):
    def __init__(self, app):
        self.text_control = FormattedTextControl(text='Debug')
        super().__init__(content=self.text_control, always_hide_cursor=True)
        self.app = app

    def update(self):
        t = arrow.get().format('YY-MM-DD, hh:mm:ss')
        proj = self.app.display_window.get_projected_coords(self.app.universe.positions)
        object_summaries = []
        for i in range(min(30, self.app.universe.entity_count)):
            object_summaries.append('\n'.join([
                f'<h3>{i:>2}.{CELESTIAL_NAMES[i]}</h3>',
                f'<red>Pos</red>: <code>{format_latlong(proj[i])}</code> [{format_vector(self.app.universe.positions[i])}]',
                f'<red>Vel</red>: <code>{np.linalg.norm(self.app.universe.velocities[i]):.4f}</code> [{format_vector(self.app.universe.velocities[i])}]',
            ]))
        self.text_control.text = HTML('\n'.join([
            f'<h1>Simulation</h1>',
            f'<red>Auto sim</red>: <code>{self.app.auto_sim}</code>',
            f'<red>Tick</red>: <code>{self.app.universe.tick}</code>',
            f'<h2>Celestial Names</h2>',
            '\n'.join(object_summaries),
        ]))
