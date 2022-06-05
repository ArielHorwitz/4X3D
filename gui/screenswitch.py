from loguru import logger

from prompt_toolkit.layout.containers import Window, VSplit, HSplit, ConditionalContainer
from prompt_toolkit.widgets import Frame
from prompt_toolkit.filters import Condition
from gui import SizeAwareFormattedTextControl


class ScreenSwitcher(VSplit):
    def __init__(self, app, screens):
        """
        Parameter screens is a dictionary with keys of screen names and
        values of list of window names.
        """
        self.app = app
        assert len(screens) > 0
        self.config = screens
        self.screen_names = list(screens.keys())
        self.screens = []
        self.current_index = 0
        containers = []
        for i, (name, windows) in enumerate(self.config.items()):
            screen = Screen(app=self.app, window_names=windows)
            self.screens.append(screen)
            con = ConditionalContainer(
                content=screen,
                filter=Condition(lambda i=i: self.current_index==i),
            )
            containers.append(con)
        super().__init__(containers)

    @property
    def current_screen(self):
        return self.screens[self.current_index]

    def next_screen(self):
        self.current_index += 1
        self.current_index %= len(self.screens)

    def prev_screen(self):
        self.current_index -= 1
        self.current_index %= len(self.screens)

    def switch_to(self, index):
        if isinstance(index, str):
            index = self.screen_names.index(index)
        self.current_index = index

    def update(self):
        self.current_screen.update()


class Screen(VSplit):
    def __init__(self, app, window_names):
        self.app = app
        self.window_names = window_names
        self.text_controls = {}
        self.windows = {}
        frames = []
        for name in window_names:
            tc = self.text_controls[name] = SizeAwareFormattedTextControl()
            win = self.windows[name] = Window(content=tc)
            frames.append(Frame(title=f'Window: {name}', body=win))
        super().__init__(frames)

    def update(self):
        for name in self.window_names:
            size = self.text_controls[name].last_size
            self.text_controls[name].text = self.app.get_window_content(name, size)
