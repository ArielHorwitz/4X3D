from loguru import logger
import json
from util.layout import WSubLayout as WSub, HSubLayout as HSub, VSubLayout as VSub
from util.config import CONFIG_DATA

aspect_ratio = CONFIG_DATA['ASPECT_RATIO']

DEFAULT_LAYOUT = {
    'console': HSub([
        WSub('console'),
        VSub(width=75, children=[
            WSub('browser'),
            WSub('feedback', height=15),
        ]),
    ]),
    'home': HSub([
        VSub(children=[
            WSub('browser'),
            WSub('console', height=11),
        ]),
        VSub(width=75, children=[
            WSub('display'),
            WSub('cockpit', height=11),
        ]),
    ]),
    'cockpit': HSub([
        VSub(width=75, children=[
            WSub('cockpit', height=11),
            WSub('browser'),
            WSub('feedback', height=2),
        ]),
        WSub('display'),
    ]),
    'debug': HSub([
        VSub(children=[
            HSub(height=20, children=[
                WSub('debug'),
                WSub('browser'),
            ]),
            WSub('console'),
        ]),
        WSub('events', width=100),
    ]),
}


def export_layout(layouts):
    return {name: export_sublayout(sub) for name, sub in layouts.items()}


def export_sublayout(sublayout):
    assert any([
        isinstance(sublayout, WSub),
        isinstance(sublayout, HSub),
        isinstance(sublayout, VSub)
    ])

    if isinstance(sublayout, WSub):
        d = {'sublayout': 'win', 'window': sublayout.window}
        if sublayout.width != WSub().width:
            d['width'] = sublayout.width
        if sublayout.height != WSub().height:
            d['height'] = sublayout.height
        return d

    cls_name, cls = ('h', HSub) if isinstance(sublayout, HSub) else ('v', VSub)
    children = [export_sublayout(child) for child in sublayout.children]
    d = {'sublayout': cls_name, 'children': children}
    if sublayout.width != cls().width:
        d['width'] = sublayout.width
    if sublayout.height != cls().height:
        d['height'] = sublayout.height
    return d


def import_layout(layouts):
    return {name: import_sublayout(sub) for name, sub in layouts.items()}


def import_sublayout(sublayout):
    assert'sublayout' in sublayout
    cls = sublayout['sublayout']
    assert cls in ['win', 'h', 'v']
    kwargs = {k: v for k, v in sublayout.items() if k != 'sublayout'}
    if cls == 'win':
        assert 'window' in sublayout
        return WSub(**kwargs)
    cls = HSub if cls == 'h' else VSub
    kwargs['children'] = [import_sublayout(child) for child in sublayout['children']]
    return cls(**kwargs)


def test():
    exported = export_layout(DEFAULT_LAYOUT)
    imported = import_layout(exported)
    double_exported = export_layout(imported)
    e = json.dumps(exported)
    e2 = json.dumps(double_exported)
    success = e == e2
    if not success:
        m = '\n'.join([
            f'DEFAULT_LAYOUTS: {DEFAULT_LAYOUTS}',
            f'       exported: {e}',
            f'       imported: {imported}',
            f'double exported: {e2}',
        ])
        logger.error(m)
        raise RuntimeError(f'Layout import/export fail (see logs for details)')
    logger.info(f'Layout import/export success.')


test()
