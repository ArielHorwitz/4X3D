
import arrow
from prompt_toolkit.layout.containers import Window, HSplit, VSplit
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import HTML

from gui import window_size, tag


class Prompt(HSplit):
    def __init__(self, app, handler):
        self.app = app
        self.prompt_text = Window(content=FormattedTextControl())
        self.prompt_input = TextArea(multiline=False, accept_handler=handler)
        prompt = VSplit([self.prompt_text, self.prompt_input], height=1)
        self.status_bar = FormattedTextControl(text='Loading...')
        status = Window(content=self.status_bar)
        super().__init__([prompt, status], height=2)

    def update(self):
        s = tag('cyan', f'{tag("orange", "dev")} @ {tag("brown", "Space")} $ ')
        if not self.app.hotkeys_enabled():
            s = tag('bold', s)
        self.prompt_text.content.text = HTML(s)
        self.prompt_text.width = self.prompt_text.content.preferred_width(30)
        size = f'{window_size().columns}×{window_size().lines} ({self.app.display_window.width}×{self.app.display_window.height})'
        self.status_bar.text = HTML(tag('cyan', ' | ').join([
            tag('code', str(arrow.get().format('YY-MM-DD, hh:mm:ss'))),
            tag('code', size),
            tag('code', f'>> {self.app.feedback_str}'),
            tag('white', f'{self.app.debug_str}'),
        ]))

    def focus(self):
        self.app.root_layout.focus(self.prompt_input)
