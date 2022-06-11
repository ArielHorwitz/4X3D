from loguru import logger

from prompt_toolkit.layout import Dimension
from prompt_toolkit.layout.containers import Window, VSplit, HSplit, ConditionalContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.widgets import Frame
from prompt_toolkit.filters import Condition

from util.layout import WSubLayout, VSubLayout


class ScreenSwitcher(VSplit):
    def __init__(self, app, layout):
        self.app = app
        assert len(layout) > 0
        self.screen_names = list(layout.keys())
        self.screens = []
        self.current_index = 0
        containers = []
        for i, (screen_name, sublayout) in enumerate(layout.items()):
            screen = Screen(app=self.app, name=screen_name, sublayout=sublayout)
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

    def __len__(self):
        return len(self.screens)


class Screen(VSplit):
    def __init__(self, app, name, sublayout):
        logger.info(f'Building Screen {name}: {sublayout}')
        self.app = app
        self.name = name
        root_container, self.text_controls = self.get_sublayout(sublayout)
        if len(self.text_controls) == 0:
            m = f'Screen {name} built without any text controls'
            logger.error(m)
            raise RuntimeError(m)
        super().__init__([root_container])

    def update(self):
        for name, tc in self.text_controls.items():
            size = tc.last_size
            r = self.app.get_window_content(name, size)
            if r is not None:
                tc.text = HTML(r)

    @classmethod
    def get_sublayout(cls, sublayout):
        width = Dimension(min=1, max=sublayout.width)
        height = Dimension(min=1, max=sublayout.height)
        if isinstance(sublayout, WSubLayout):
            tc = SizeAwareFormattedTextControl()
            wname = sublayout.window
            win = Window(content=tc, ignore_content_width=True, ignore_content_height=True)
            win.width, win.height = width, height
            return Frame(title=f'Window: {wname}', body=win), {wname: tc}
        # Is splitter, recursively get child sublayouts
        all_children = []
        all_tcs =  {}
        for child in sublayout.children:
            new_child, tcs = cls.get_sublayout(child)
            all_children.append(new_child)
            all_tcs |= tcs
        # A VSubLayout is a panel with windows that span vertically
        # hence horizontal splitter for VSubLayout, and vice versa
        cls = HSplit if isinstance(sublayout, VSubLayout) else VSplit
        sb = cls(all_children)
        sb.width, sb.height = width, height
        return sb, all_tcs


class SizeAwareFormattedTextControl(FormattedTextControl):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.last_size = 1, 1

    def create_content(self, width, height):
        self.last_size = width, height
        return super().create_content(width, height)
