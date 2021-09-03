import logging

from fontTools import ttLib
from fontTools.pens.hashPointPen import HashPointPen
from fontTools.ttLib.tables._g_l_y_f import (
    OVERLAP_COMPOUND,
    ROUND_XY_TO_GRID,
    USE_MY_METRICS,
)

from ufo2ft.constants import (
    OBJECT_LIBS_KEY,
    TRUETYPE_INSTRUCTIONS_KEY,
    TRUETYPE_METRICS_KEY,
    TRUETYPE_OVERLAP_KEY,
    TRUETYPE_ROUND_KEY,
)

logger = logging.getLogger(__name__)


class InstructionCompiler(object):
    def __init__(self, ufo, ttf):
        self.ufo = ufo
        self.font = ttf

    def _check_glyph_hash(self, glyph, ttdata):
        # Check if the glyph hash in the ufo matches the current outlines
        hash_pen = HashPointPen(glyph.width, self.ufo)
        glyph.drawPoints(hash_pen)
        glyph_id = ttdata.get("id", None)
        if glyph_id is None:
            # The glyph hash is required
            logger.error(
                f"Glyph hash missing, glyph '{glyph.name}' will have "
                "no instructions in font."
            )
            return False

        if glyph_id != hash_pen.hash:
            logger.error(
                f"Glyph hash mismatch, glyph '{glyph.name}' will have "
                "no instructions in font."
            )
            return False
        return True

    def _check_tt_data_format(self, ttdata):
        # Make sure we understand the format version
        formatVersion = ttdata.get("formatVersion", None)
        if int(formatVersion) != 1:
            raise NotImplementedError(
                f"Unknown formatVersion {formatVersion} "
                "for instructions in glyph '{name}'."
            )

    def _compile_program(self, key, table_tag):
        assert table_tag in ("prep", "fpgm")
        ttdata = self.ufo.lib.get(TRUETYPE_INSTRUCTIONS_KEY, None)
        if ttdata:
            formatVersion = ttdata.get("formatVersion", None)
            if int(formatVersion) != 1:
                raise NotImplementedError(
                    f"Unknown formatVersion {formatVersion} "
                    f"for instructions in lib key '{key}'."
                )
            asm = ttdata.get(key, None)
            if asm is not None:
                self.font[table_tag] = table = ttLib.newTable(table_tag)
                table.program = ttLib.tables.ttProgram.Program()
                table.program.fromAssembly(asm)

    def _compile_tt_glyph(self, name):
        glyph = self.ufo[name]
        ttdata = glyph.lib.get(TRUETYPE_INSTRUCTIONS_KEY, None)
        if name not in self.font["glyf"]:
            if ttdata is not None:
                logger.debug(
                    f"Glyph '{name}' not found in font, "
                    "skipping compilation of TrueType instructions "
                    "for this glyph."
                )
            return

        ttglyph = self.font["glyf"][name]
        if ttdata is not None:
            self._compile_tt_glyph_program(glyph, ttglyph, ttdata)
        if ttglyph.isComposite():
            self._set_composite_flags(glyph, ttglyph)

    def _compile_tt_glyph_program(self, glyph, ttglyph, ttdata):
        self._check_tt_data_format(ttdata)
        if not self._check_glyph_hash(glyph, ttdata):
            return

        # Compile the glyph program
        asm = ttdata.get("assembly", None)
        if asm is None:
            # The "assembly" key is required.
            logger.error(
                f"Glyph assembly missing, glyph '{glyph.name}' will have "
                "no instructions in font."
            )
            return

        ttglyph.program = ttLib.tables.ttProgram.Program()
        ttglyph.program.fromAssembly(asm)

    def _set_composite_flags(self, glyph, ttglyph):
        # Remove empty glyph programs from composite glyphs
        if hasattr(ttglyph, "program") and not ttglyph.program:
            delattr(ttglyph, "program")

        # Set component flags

        if len(ttglyph.components) != len(glyph.components):
            logger.error(
                "Number of components differ between UFO and TTF "
                f"in glyph '{glyph.name}' ({len(glyph.components)} vs. "
                f"{len(ttglyph.components)}, not setting component flags from"
                "UFO. They may still be set heuristically."
            )
            return

        # We need to decide when to set the flags.
        # Let's assume if any lib key is not there, or the component
        # doesn't have an identifier, we should leave the flags alone.

        # Keep track of which component has the USE_MY_METRICS flag
        use_my_metrics_comp = None

        for i, c in enumerate(ttglyph.components):
            ufo_component_id = glyph.components[i].identifier
            if (
                ufo_component_id is not None
                and OBJECT_LIBS_KEY in glyph.lib
                and ufo_component_id in glyph.lib[OBJECT_LIBS_KEY]
                and (
                    TRUETYPE_ROUND_KEY in glyph.lib[OBJECT_LIBS_KEY][ufo_component_id]
                    or TRUETYPE_METRICS_KEY
                    in glyph.lib[OBJECT_LIBS_KEY][ufo_component_id]
                )
            ):
                component_lib = glyph.lib[OBJECT_LIBS_KEY][ufo_component_id]

                # https://github.com/googlefonts/ufo2ft/pull/425 recommends
                # to always set the ROUND_XY_TO_GRID flag, so we only
                # unset it if explicitly done so in the lib
                if component_lib.get(TRUETYPE_ROUND_KEY, True):
                    c.flags |= ROUND_XY_TO_GRID
                else:
                    c.flags &= ~ROUND_XY_TO_GRID

                if component_lib.get(TRUETYPE_METRICS_KEY, False):
                    c.flags &= ~USE_MY_METRICS
                    if use_my_metrics_comp:
                        logger.warning(
                            "Ignoring USE_MY_METRICS flag on component "
                            f"'{ufo_component_id}' because it has been set on "
                            f"component '{use_my_metrics_comp}' already "
                            f"in glyph {glyph.name}."
                        )
                    else:
                        c.flags |= USE_MY_METRICS
                        use_my_metrics_comp = ufo_component_id

            if i == 0 and TRUETYPE_OVERLAP_KEY in glyph.lib:
                # Set OVERLAP_COMPOUND on the first component only
                if glyph.lib.get(TRUETYPE_OVERLAP_KEY, False):
                    c.flags |= OVERLAP_COMPOUND
                else:
                    c.flags &= ~OVERLAP_COMPOUND

    def compile_fpgm(self):
        self._compile_program("fontProgram", "fpgm")

    def compile_glyf(self):
        for name in sorted(self.ufo.keys()):
            self._compile_tt_glyph(name)

    def compile_maxp(self):
        maxp = self.font["maxp"]
        ttdata = self.ufo.lib.get(TRUETYPE_INSTRUCTIONS_KEY, None)
        if ttdata:
            for name in (
                "maxStorage",
                "maxFunctionDefs",
                "maxInstructionDefs",
                "maxStackElements",
                # "maxSizeOfInstructions",  # Is recalculated below
                "maxZones",
                "maxTwilightPoints",
            ):
                value = ttdata.get(name, None)
                if value is not None:
                    setattr(maxp, name, value)

        # Recalculate maxp.maxSizeOfInstructions
        sizes = [
            len(ttglyph.program.getBytecode())
            for ttglyph in self.font["glyf"].glyphs.values()
            if hasattr(ttglyph, "program")
        ]
        maxp.maxSizeOfInstructions = max(sizes, default=0)

    def compile_prep(self):
        self._compile_program("controlValueProgram", "prep")

    def compile(self):
        self.compile_fpgm()
        self.compile_prep()
        self.compile_glyf()
        # maxp depends on the other programs, to it needs to be last
        self.compile_maxp()