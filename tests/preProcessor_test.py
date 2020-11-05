from __future__ import print_function, division, absolute_import, unicode_literals
import os
import logging
import ufo2ft
from ufo2ft.preProcessor import (
    TTFPreProcessor,
    TTFInterpolatablePreProcessor,
    _init_explode_color_layer_glyphs_filter,
)
from ufo2ft.filters import UFO2FT_FILTERS_KEY
from ufo2ft.filters.explodeColorLayerGlyphs import ExplodeColorLayerGlyphsFilter
from cu2qu.ufo import CURVE_TYPE_LIB_KEY
from fontTools import designspaceLib
from ufo2ft.constants import (
    COLOR_LAYERS_KEY,
    COLOR_LAYER_MAPPING_KEY,
    COLOR_PALETTES_KEY,
)
import pytest


def getpath(filename):
    """
    Return the path of the file.

    Args:
        filename: (str): write your description
    """
    dirname = os.path.dirname(__file__)
    return os.path.join(dirname, "data", filename)


def glyph_has_qcurve(ufo, glyph_name):
    """
    Check if a glyph has a glyph.

    Args:
        ufo: (todo): write your description
        glyph_name: (str): write your description
    """
    return any(
        s.segmentType == "qcurve" for contour in ufo[glyph_name] for s in contour
    )


class TTFPreProcessorTest(object):
    def test_no_inplace(self, FontClass):
        """
        Test if the ufo.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
        """
        ufo = FontClass(getpath("TestFont.ufo"))

        glyphSet = TTFPreProcessor(ufo, inplace=False).process()

        assert not glyph_has_qcurve(ufo, "c")
        assert glyph_has_qcurve(glyphSet, "c")
        assert CURVE_TYPE_LIB_KEY not in ufo.layers.defaultLayer.lib

    def test_inplace_remember_curve_type(self, FontClass, caplog):
        """
        Test if the ufo type is a ufo.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
            caplog: (todo): write your description
        """
        caplog.set_level(logging.ERROR)

        ufo = FontClass(getpath("TestFont.ufo"))

        assert CURVE_TYPE_LIB_KEY not in ufo.lib
        assert CURVE_TYPE_LIB_KEY not in ufo.layers.defaultLayer.lib
        assert not glyph_has_qcurve(ufo, "c")

        TTFPreProcessor(ufo, inplace=True, rememberCurveType=True).process()

        assert CURVE_TYPE_LIB_KEY not in ufo.lib
        assert ufo.layers.defaultLayer.lib[CURVE_TYPE_LIB_KEY] == "quadratic"
        assert glyph_has_qcurve(ufo, "c")

        logger = "ufo2ft.filters.cubicToQuadratic"
        with caplog.at_level(logging.INFO, logger=logger):
            TTFPreProcessor(ufo, inplace=True, rememberCurveType=True).process()

        assert len(caplog.records) == 1
        assert "Curves already converted to quadratic" in caplog.text
        assert glyph_has_qcurve(ufo, "c")

    def test_inplace_no_remember_curve_type(self, FontClass):
        """
        Test if the ufo exists in the current.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
        """
        ufo = FontClass(getpath("TestFont.ufo"))

        assert CURVE_TYPE_LIB_KEY not in ufo.lib
        assert CURVE_TYPE_LIB_KEY not in ufo.layers.defaultLayer.lib

        for _ in range(2):
            TTFPreProcessor(ufo, inplace=True, rememberCurveType=False).process()

            assert CURVE_TYPE_LIB_KEY not in ufo.lib
            assert CURVE_TYPE_LIB_KEY not in ufo.layers.defaultLayer.lib
            assert glyph_has_qcurve(ufo, "c")


class TTFInterpolatablePreProcessorTest(object):
    def test_no_inplace(self, FontClass):
        """
        Test whether the ufo.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
        """
        ufo1 = FontClass(getpath("TestFont.ufo"))
        ufo2 = FontClass(getpath("TestFont.ufo"))
        ufos = [ufo1, ufo2]

        assert CURVE_TYPE_LIB_KEY not in ufo1.lib
        assert CURVE_TYPE_LIB_KEY not in ufo1.layers.defaultLayer.lib
        assert not glyph_has_qcurve(ufo1, "c")

        glyphSets = TTFInterpolatablePreProcessor(ufos, inplace=False).process()

        for i in range(2):
            assert glyph_has_qcurve(glyphSets[i], "c")
            assert CURVE_TYPE_LIB_KEY not in ufos[i].lib
            assert CURVE_TYPE_LIB_KEY not in ufos[i].layers.defaultLayer.lib

    def test_inplace_remember_curve_type(self, FontClass):
        """
        Test if a ufo type.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
        """
        ufo1 = FontClass(getpath("TestFont.ufo"))
        ufo2 = FontClass(getpath("TestFont.ufo"))
        ufos = [ufo1, ufo2]

        assert CURVE_TYPE_LIB_KEY not in ufo1.lib
        assert CURVE_TYPE_LIB_KEY not in ufo1.layers.defaultLayer.lib
        assert not glyph_has_qcurve(ufo1, "c")

        TTFInterpolatablePreProcessor(
            ufos, inplace=True, rememberCurveType=True
        ).process()

        assert ufo1.layers.defaultLayer.lib[CURVE_TYPE_LIB_KEY] == "quadratic"
        assert glyph_has_qcurve(ufo1, "c")
        assert ufo2.layers.defaultLayer.lib[CURVE_TYPE_LIB_KEY] == "quadratic"
        assert glyph_has_qcurve(ufo2, "c")

    def test_inplace_no_remember_curve_type(self, FontClass):
        """
        Test if the ufo exists.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
        """
        ufo1 = FontClass(getpath("TestFont.ufo"))
        ufo2 = FontClass(getpath("TestFont.ufo"))
        ufos = [ufo1, ufo2]

        for _ in range(2):
            TTFInterpolatablePreProcessor(
                ufos, inplace=True, rememberCurveType=False
            ).process()

            assert CURVE_TYPE_LIB_KEY not in ufo1.layers.defaultLayer.lib
            assert CURVE_TYPE_LIB_KEY not in ufo2.layers.defaultLayer.lib
            assert glyph_has_qcurve(ufo1, "c")
            assert glyph_has_qcurve(ufo2, "c")

    def test_custom_filters(self, FontClass):
        """
        Test for glyph filters.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
        """
        ufo1 = FontClass(getpath("TestFont.ufo"))
        ufo1.lib[UFO2FT_FILTERS_KEY] = [
            {"name": "transformations", "kwargs": {"OffsetX": -40}, "pre": True}
        ]
        ufo2 = FontClass(getpath("TestFont.ufo"))
        ufo2.lib[UFO2FT_FILTERS_KEY] = [
            {"name": "transformations", "kwargs": {"OffsetY": 10}}
        ]
        ufos = [ufo1, ufo2]

        glyphSets = TTFInterpolatablePreProcessor(ufos).process()

        assert (glyphSets[0]["a"][0][0].x - glyphSets[1]["a"][0][0].x) == -40
        assert (glyphSets[1]["a"][0][0].y - glyphSets[0]["a"][0][0].y) == 10


class SkipExportGlyphsTest(object):
    def test_skip_export_glyphs_filter(self, FontClass):
        """
        Test that all glyph glyphs have a glyph.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
        """
        from ufo2ft.util import _GlyphSet

        ufo = FontClass(getpath("IncompatibleMasters/NewFont-Regular.ufo"))
        skipExportGlyphs = ["b", "d"]
        glyphSet = _GlyphSet.from_layer(ufo, skipExportGlyphs=skipExportGlyphs)

        assert set(glyphSet.keys()) == set(["a", "c", "e", "f"])
        assert len(glyphSet["a"]) == 1
        assert not glyphSet["a"].components
        assert len(glyphSet["c"]) == 5  # 4 "d" components decomposed plus 1 outline
        assert list(c.baseGlyph for c in glyphSet["c"].components) == ["a"]
        assert len(glyphSet["e"]) == 1
        assert list(c.baseGlyph for c in glyphSet["e"].components) == ["c", "c"]
        assert not glyphSet["f"]
        assert list(c.baseGlyph for c in glyphSet["f"].components) == ["a", "a"]

    def test_skip_export_glyphs_filter_nested(self, FontClass):
        """
        Test for glyph glyphs.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
        """
        from ufo2ft.util import _GlyphSet

        ufo = FontClass()
        glyph_N = ufo.newGlyph("N")
        glyph_N.width = 100
        pen = glyph_N.getPen()
        pen.moveTo((0, 0))
        pen.lineTo((300, 0))
        pen.lineTo((300, 400))
        pen.lineTo((0, 400))
        pen.closePath()

        glyph_o = ufo.newGlyph("o")
        glyph_o.width = 100
        pen = glyph_o.getPen()
        pen.moveTo((0, 0))
        pen.lineTo((300, 0))
        pen.lineTo((300, 300))
        pen.lineTo((0, 300))
        pen.closePath()

        glyph_onumero = ufo.newGlyph("_o.numero")
        glyph_onumero.width = 100
        pen = glyph_onumero.getPen()
        pen.addComponent("o", (-1, 0, 0, -1, 0, 100))
        pen.moveTo((0, 0))
        pen.lineTo((300, 0))
        pen.lineTo((300, 50))
        pen.lineTo((0, 50))
        pen.closePath()

        glyph_numero = ufo.newGlyph("numero")
        glyph_numero.width = 200
        pen = glyph_numero.getPen()
        pen.addComponent("N", (1, 0, 0, 1, 0, 0))
        pen.addComponent("_o.numero", (1, 0, 0, 1, 400, 0))

        skipExportGlyphs = ["_o.numero"]
        glyphSet = _GlyphSet.from_layer(ufo, skipExportGlyphs=skipExportGlyphs)

        assert len(glyphSet["numero"].components) == 1  # The "N" component
        assert len(glyphSet["numero"]) == 2  # The two contours of "o" and "_o.numero"

    def test_skip_export_glyphs_designspace(self, FontClass):
        """
        Skip glyphspace glyphs.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
        """
        # Designspace has a public.skipExportGlyphs lib key excluding "b" and "d".
        designspace = designspaceLib.DesignSpaceDocument.fromfile(
            getpath("IncompatibleMasters/IncompatibleMasters.designspace")
        )
        for source in designspace.sources:
            source.font = FontClass(
                getpath(os.path.join("IncompatibleMasters", source.filename))
            )
        ufo2ft.compileInterpolatableTTFsFromDS(designspace, inplace=True)

        for source in designspace.sources:
            assert source.font.getGlyphOrder() == [".notdef", "a", "c", "e", "f"]
            gpos_table = source.font["GPOS"].table
            assert gpos_table.LookupList.Lookup[0].SubTable[0].Coverage.glyphs == [
                "a",
                "e",
                "f",
            ]
            glyphs = source.font["glyf"].glyphs
            for g in glyphs.values():
                g.expand(source.font["glyf"])
            assert glyphs["a"].numberOfContours == 1
            assert not hasattr(glyphs["a"], "components")
            assert glyphs["c"].numberOfContours == 6
            assert not hasattr(glyphs["c"], "components")
            assert glyphs["e"].numberOfContours == 13
            assert not hasattr(glyphs["e"], "components")
            assert glyphs["f"].isComposite()

    def test_skip_export_glyphs_multi_ufo(self, FontClass):
        """
        Test that all glyphs have the ufo.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
        """
        # Bold has a public.skipExportGlyphs lib key excluding "b", "d" and "f".
        ufo1 = FontClass(getpath("IncompatibleMasters/NewFont-Regular.ufo"))
        ufo2 = FontClass(getpath("IncompatibleMasters/NewFont-Bold.ufo"))
        fonts = ufo2ft.compileInterpolatableTTFs([ufo1, ufo2], inplace=True)

        for font in fonts:
            assert set(font.getGlyphOrder()) == {".notdef", "a", "c", "e"}
            gpos_table = font["GPOS"].table
            assert gpos_table.LookupList.Lookup[0].SubTable[0].Coverage.glyphs == ["a"]
            glyphs = font["glyf"].glyphs
            for g in glyphs.values():
                g.expand(font["glyf"])
            assert glyphs["a"].numberOfContours == 1
            assert not hasattr(glyphs["a"], "components")
            assert glyphs["c"].numberOfContours == 6
            assert not hasattr(glyphs["c"], "components")
            assert glyphs["e"].numberOfContours == 13
            assert not hasattr(glyphs["e"], "components")

    def test_skip_export_glyphs_single_ufo(self, FontClass):
        """
        Test that all glyphs have a single glyph.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
        """
        # UFO has a public.skipExportGlyphs lib key excluding "b", "d" and "f".
        ufo = FontClass(getpath("IncompatibleMasters/NewFont-Bold.ufo"))
        font = ufo2ft.compileTTF(ufo, inplace=True)

        assert set(font.getGlyphOrder()) == {".notdef", "a", "c", "e"}
        gpos_table = font["GPOS"].table
        assert gpos_table.LookupList.Lookup[0].SubTable[0].Coverage.glyphs == ["a"]
        glyphs = font["glyf"].glyphs
        for g in glyphs.values():
            g.expand(font["glyf"])
        assert glyphs["a"].numberOfContours == 1
        assert not hasattr(glyphs["a"], "components")
        assert glyphs["c"].numberOfContours == 6
        assert not hasattr(glyphs["c"], "components")
        assert glyphs["e"].numberOfContours == 13
        assert not hasattr(glyphs["e"], "components")


@pytest.fixture
def color_ufo(FontClass):
    """
    Return a ufo of a ufo.

    Args:
        FontClass: (todo): write your description
    """
    ufo = FontClass()
    ufo.lib[COLOR_PALETTES_KEY] = [[(1, 0.3, 0.1, 1), (0, 0.4, 0.8, 1)]]
    return ufo


class InitExplodeColorLayerGlyphsFilterTest(object):
    def test_no_color_palettes(self, FontClass):
        """
        Test if the color layer for a new layer.

        Args:
            self: (todo): write your description
            FontClass: (todo): write your description
        """
        ufo = FontClass()
        filters = []
        _init_explode_color_layer_glyphs_filter(ufo, filters)
        assert not filters

    def test_no_color_layer_mapping(self, color_ufo):
        """
        Set the layer color_uf.

        Args:
            self: (todo): write your description
            color_ufo: (str): write your description
        """
        filters = []
        _init_explode_color_layer_glyphs_filter(color_ufo, filters)
        assert not filters

    def test_explicit_color_layers(self, color_ufo):
        """
        Return a list of all layers to be included.

        Args:
            self: (todo): write your description
            color_ufo: (str): write your description
        """
        color_ufo.lib[COLOR_LAYERS_KEY] = {"a": [("a.z_0", 1), ("a.z_1", 0)]}
        filters = []
        _init_explode_color_layer_glyphs_filter(color_ufo, filters)
        assert not filters

    def test_font_color_layer_mapping(self, color_ufo):
        """
        Test if the ufo layer.

        Args:
            self: (todo): write your description
            color_ufo: (str): write your description
        """
        color_ufo.lib[COLOR_LAYER_MAPPING_KEY] = [("z_0", 1), ("z_1", 0)]
        filters = []
        _init_explode_color_layer_glyphs_filter(color_ufo, filters)
        assert isinstance(filters[0], ExplodeColorLayerGlyphsFilter)

    def test_glyph_color_layer_mapping(self, color_ufo):
        """
        Test if the ufo color_layer.

        Args:
            self: (todo): write your description
            color_ufo: (todo): write your description
        """
        color_ufo.newGlyph("a").lib[COLOR_LAYER_MAPPING_KEY] = [("z_0", 0), ("z_1", 1)]
        filters = []
        _init_explode_color_layer_glyphs_filter(color_ufo, filters)
        assert isinstance(filters[0], ExplodeColorLayerGlyphsFilter)
