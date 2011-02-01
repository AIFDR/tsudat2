#!/usr/bin/env python

"""Utility routines used by URSAPI."""


def colour_code_val(min_val, val, max_val):
    """Colour code a value in a given range.

    min_val  minimum range value
    val      the value to colour-code
    max_val  maximum range value

    Returns a colour string '#RRGGBB'.
    The colour mapping is the GA 'hazmap' mapping.
    """

    val = float(val)

    # map 'val' to range 0->510 over [min_val, max_val]
    range_value = int(510 * (val - min_val) / (max_val - min_val))

    # convert range value in [0, 510] to RGB
    if range_value <= 255:
        r = range_value
        g = 255
    else:
        r = 255
        g = 510 - range_value

    return '#%02x%02x00' % (r, g)
