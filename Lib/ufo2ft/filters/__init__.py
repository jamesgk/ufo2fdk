import importlib
import logging
import re
from inspect import getfullargspec, isclass

from ufo2ft.constants import FILTERS_KEY as UFO2FT_FILTERS_KEY  # keep previous name
from ufo2ft.util import _kwargsEval

from .base import BaseFilter
from .cubicToQuadratic import CubicToQuadraticFilter
from .decomposeComponents import DecomposeComponentsFilter
from .decomposeTransformedComponents import DecomposeTransformedComponentsFilter
from .explodeColorLayerGlyphs import ExplodeColorLayerGlyphsFilter
from .flattenComponents import FlattenComponentsFilter
from .propagateAnchors import PropagateAnchorsFilter
from .removeOverlaps import RemoveOverlapsFilter
from .sortContours import SortContoursFilter
from .transformations import TransformationsFilter

__all__ = [
    "BaseFilter",
    "CubicToQuadraticFilter",
    "DecomposeComponentsFilter",
    "DecomposeTransformedComponentsFilter",
    "ExplodeColorLayerGlyphsFilter",
    "FlattenComponentsFilter",
    "PropagateAnchorsFilter",
    "RemoveOverlapsFilter",
    "SortContoursFilter",
    "TransformationsFilter",
    "loadFilters",
    "loadFilterFromString",
]


logger = logging.getLogger(__name__)


def getFilterClass(filterName, pkg="ufo2ft.filters"):
    """Given a filter name, import and return the filter class.
    By default, filter modules are searched within the ``ufo2ft.filters``
    package.
    """
    # TODO add support for third-party plugin discovery?
    # if filter name is 'Foo Bar', the module should be called 'fooBar'
    filterName = filterName.replace(" ", "")
    moduleName = filterName[0].lower() + filterName[1:]
    module = importlib.import_module(".".join([pkg, moduleName]))
    # if filter name is 'Foo Bar', the class should be called 'FooBarFilter'
    className = filterName[0].upper() + filterName[1:] + "Filter"
    return getattr(module, className)


def loadFilters(ufo):
    """Parse custom filters from the ufo's lib.plist. Return two lists,
    one for the filters that are applied before decomposition of composite
    glyphs, another for the filters that are applied after decomposition.
    """
    preFilters, postFilters = [], []
    for filterDict in ufo.lib.get(UFO2FT_FILTERS_KEY, []):
        namespace = filterDict.get("namespace", "ufo2ft.filters")
        try:
            filterClass = getFilterClass(filterDict["name"], namespace)
        except (ImportError, AttributeError):
            from pprint import pformat

            logger.exception("Failed to load filter: %s", pformat(filterDict))
            continue
        filterObj = filterClass(
            include=filterDict.get("include"),
            exclude=filterDict.get("exclude"),
            *filterDict.get("args", []),
            **filterDict.get("kwargs", {}),
        )
        if filterDict.get("pre"):
            preFilters.append(filterObj)
        else:
            postFilters.append(filterObj)
    return preFilters, postFilters


_filterSpecRE = re.compile(
    r"(?:([\w\.]+)::)?"  # MODULE_NAME + '::'
    r"(\w+)"  # CLASS_NAME [required]
    r"(?:\((.*)\))?"  # (KWARGS)
)


def isValidFilter(klass):
    """Return True if 'klass' is a valid filter class.
    A valid filter class is a class (of type 'type'), that has
    a '__call__' (bound method), with the signature matching the same method
    from the BaseFilter class:

           def __call__(self, font, feaFile, compiler=None)
    """
    if not isclass(klass):
        logger.error("{klass!r} is not a class")
        return False
    if not callable(klass):
        logger.error("{klass!r} is not callable")
        return False
    if getfullargspec(klass.__call__).args != getfullargspec(BaseFilter.__call__).args:
        logger.error("{klass!r} '__call__' method has incorrect signature", klass)
        return False
    return True


def loadFilterFromString(spec):
    """Take a string specifying a filter class to load (either a built-in
    writer or one defined in an external, user-defined module), initialize it
    with given options and return the filter object.

    The string must conform to the following notation:
    - an optional python module, followed by '::'
    - a required class name; the class must have a method called 'filter'
      with the same signature as the BaseFilter.
    - an optional list of keyword-only arguments enclosed by parentheses

    Raises ValueError if the string doesn't conform to this specification;
    TypeError if imported name is not a filter class; and ImportError if the
    user-defined module cannot be imported.

    Examples:

    >>> loadFilterFromString("ufo2ft.filters.removeOverlaps::RemoveOverlapsFilter")
    <ufo2ft.filters.removeOverlaps.RemoveOverlapsFilter object at ...>
    """
    spec = spec.strip()
    m = _filterSpecRE.match(spec)
    if not m or (m.end() - m.start()) != len(spec):
        raise ValueError(spec)
    moduleName = m.group(1) or "ufo2ft.filters"
    className = m.group(2)
    kwargs = m.group(3)

    module = importlib.import_module(moduleName)
    klass = getattr(module, className)
    if not isValidFilter(klass):
        raise TypeError(klass)
    try:
        options = _kwargsEval(kwargs) if kwargs else {}
    except SyntaxError:
        raise ValueError("options have incorrect format: %r" % kwargs)

    # Process positional arguments
    requiredArgs = set(klass._args)
    args = requiredArgs.intersection(options.keys())
    missing = [a for a in klass._args if a not in options]
    if missing:
        raise TypeError(
            f"missing {len(missing)} required "
            f"argument{'s' if len(missing) > 1 else ''}: {', '.join(missing)}"
        )
    elif args:
        args = [options.pop(a) for a in args]
        return klass(*args, **options)
    else:
        return klass(**options)
