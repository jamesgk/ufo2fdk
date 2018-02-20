from __future__ import print_function, division, absolute_import
from ufo2ft.filters.propagateAnchors import PropagateAnchorsFilter, logger
from fontTools.misc.loggingTools import CapturingLogHandler
import defcon
import pytest


@pytest.fixture(params=[
    {
        'glyphs': [
            {
                'name': 'space',
                'width': 500,
            },
            {
                'name': 'a',
                'width': 350,
                'outline': [
                    ('moveTo', ((0, 0),)),
                    ('lineTo', ((300, 0),)),
                    ('lineTo', ((300, 300),)),
                    ('lineTo', ((0, 300),)),
                    ('closePath', ()),
                ],
                'anchors': [
                    (175, 300, 'top'),
                    (175, 0, 'bottom'),
                ],
            },
            {
                'name': 'dieresiscomb',
                'width': 0,
                'outline': [
                    ('moveTo', ((-120, 320),)),
                    ('lineTo', ((-60, 320),)),
                    ('lineTo', ((-60, 360),)),
                    ('lineTo', ((-120, 360),)),
                    ('closePath', ()),
                    ('moveTo', ((120, 320),)),
                    ('lineTo', ((60, 320),)),
                    ('lineTo', ((60, 360),)),
                    ('lineTo', ((120, 360),)),
                    ('closePath', ()),
                ],
                'anchors': [
                    (0, 300, '_top'),
                    (0, 480, 'top'),
                ],
            },
            {
                'name': 'macroncomb',
                'width': 0,
                'outline': [
                    ('moveTo', ((-120, 330),)),
                    ('lineTo', ((120, 330),)),
                    ('lineTo', ((120, 350),)),
                    ('lineTo', ((-120, 350),)),
                    ('closePath', ()),
                ],
                'anchors': [
                    (0, 300, '_top'),
                    (0, 480, 'top'),
                ],
            },
            {
                'name': 'a-cyr',
                'width': 350,
                'outline': [
                    ('addComponent', ('a', (1, 0, 0, 1, 0, 0))),
                ],
            },
            {
                'name': 'amacron',
                'width': 350,
                'outline': [
                    ('addComponent', ('a', (1, 0, 0, 1, 0, 0))),
                    ('addComponent', ('macroncomb', (1, 0, 0, 1, 175, 0))),
                ],
            },
            {
                'name': 'adieresis',
                'width': 350,
                'outline': [
                    ('addComponent', ('a', (1, 0, 0, 1, 0, 0))),
                    ('addComponent', ('dieresiscomb', (1, 0, 0, 1, 175, 0))),
                ],
            },
            {
                'name': 'amacrondieresis',
                'width': 350,
                'outline': [
                    ('addComponent', ('amacron', (1, 0, 0, 1, 0, 0))),
                    ('addComponent', ('dieresiscomb', (1, 0, 0, 1, 175, 180))),
                ],
            },
            {
                'name': 'adieresismacron',
                'width': 350,
                'outline': [
                    ('addComponent', ('a', (1, 0, 0, 1, 0, 0))),
                    ('addComponent', ('dieresiscomb', (1, 0, 0, 1, 175, 0))),
                    ('addComponent', ('macroncomb', (1, 0, 0, 1, 175, 180))),
                ],
            },
        ],
    }
])
def font(request):
    font = defcon.Font()
    for param in request.param['glyphs']:
        glyph = font.newGlyph(param['name'])
        glyph.width = param.get('width', 0)
        pen = glyph.getPen()
        for operator, operands in param.get('outline', []):
            getattr(pen, operator)(*operands)
        for x, y, name in param.get('anchors', []):
            glyph.appendAnchor(dict(x=x, y=y, name=name))
    return font


class PropagateAnchorsFilterTest(object):

    def test_empty_glyph(self, font):
        philter = PropagateAnchorsFilter(include={'space'})
        assert not philter(font)

    def test_contour_glyph(self, font):
        philter = PropagateAnchorsFilter(include={'a'})
        assert not philter(font)

    def test_single_component_glyph(self, font):
        philter = PropagateAnchorsFilter(include={'a-cyr'})
        assert philter(font) == {'a-cyr'}
        assert (
            [(a.name, a.x, a.y) for a in font['a-cyr'].anchors] ==
            [('bottom', 175, 0),
             ('top', 175, 300)]
        )

    def test_two_component_glyph(self, font):
        name = 'amacron'
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) == {name}
        assert (
            [(a.name, a.x, a.y) for a in font[name].anchors] ==
            [('bottom', 175, 0),
             ('top', 175, 480)]
        )

    def test_three_component_glyph(self, font):
        name = 'adieresismacron'
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) == {name}
        assert (
            [(a.name, a.x, a.y) for a in font[name].anchors] ==
            [('bottom', 175, 0),
             ('top', 175, 660)]
        )

    def test_nested_component_glyph(self, font):
        name = 'amacrondieresis'
        philter = PropagateAnchorsFilter(include={name})
        assert philter(font) == {name}
        assert (
            [(a.name, a.x, a.y) for a in font[name].anchors] ==
            [('bottom', 175, 0),
             ('top', 175, 660)]
        )

    def test_whole_font(self, font):
        philter = PropagateAnchorsFilter()
        modified = philter(font)
        assert modified == set(['a-cyr', 'amacron', 'adieresis',
                                'adieresismacron', 'amacrondieresis'])

    def test_logger(self, font):
        with CapturingLogHandler(logger, level="INFO") as captor:
            philter = PropagateAnchorsFilter()
            modified = philter(font)
        captor.assertRegex('Glyphs with propagated anchors: 5')
