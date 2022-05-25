
import numpy as np
import arrow
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import HTML

from gui import window_size, format_latlong, format_vector
from logic.logic import CELESTIAL_NAMES
from logic.quaternion import Quaternion as Quat


class Debug(Window):
    def __init__(self, app):
        self.text_control = FormattedTextControl(text='Debug')
        super().__init__(content=self.text_control, always_hide_cursor=True)
        self.app = app

    def update(self):
        t = arrow.get().format('YY-MM-DD, hh:mm:ss')
        proj = self.app.display_window.get_projection(self.app.universe.positions)
        camera_axis = self.app.display_window.camera_axes[0]
        object_summaries = []
        for i in range(50):
            name = f'{CELESTIAL_NAMES[i][:9]:.<10}'
            ll = ''.join(f"{f'{_:.1f}':>6}°" for _ in proj[i])
            pos = ''.join(f"{f'{_:.1f}':>6}" for _ in self.app.universe.positions[i])
            vel = ''.join(f"{f'{_:.1f}':>4}" for _ in self.app.universe.velocities[i])
            v = f'{np.linalg.norm(self.app.universe.velocities[i]):.1f}'
            object_summaries.append(f'{name}: v:{v} | pos:{pos} | dir:{ll} | v:{vel}')
        self.text_control.text = HTML('\n'.join([
            f'<h1>Simulation</h1>',
            f'<red>Auto sim</red>: <code>{self.app.auto_sim}</code>',
            f'<red>Tick</red>: <code>{self.app.universe.tick}</code>',
            f'<h2>Position / Velocity</h2>',
            '\n'.join(object_summaries),
        ]))
