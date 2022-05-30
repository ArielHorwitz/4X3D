
from prompt_toolkit.layout.containers import VSplit, ConditionalContainer
from prompt_toolkit.widgets import Frame
from prompt_toolkit.filters import Condition


class ScreenSwitcher(VSplit):
    def __init__(self, app, screens):
        self.app = app
        assert len(screens) > 0
        self.screen_names = list(screens.keys())
        self.screens = list(screens.values())
        self.current_index = 0
        super().__init__([ConditionalContainer(
            content=Frame(title=f'Screen: {self.screen_names[i]}', body=s),
            filter=Condition(lambda i=i: self.current_index==i),
        ) for i, s in enumerate(self.screens)])

    @property
    def current_screen(self):
        return self.screens[self.current_index]

    def next_screen(self):
        self.current_index += 1
        self.current_index %= len(self.screens)

    def switch_to(self, index):
        if isinstance(index, str):
            index = self.screen_names.index(index)
        self.current_index = index
