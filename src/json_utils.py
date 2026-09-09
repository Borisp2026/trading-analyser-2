"""Shared JSON writing that never emits NaN / Infinity.

Python's json module serialises float('nan') / numpy.nan as the bare tokens
`NaN`, `Infinity`, `-Infinity`. Those are valid Python but NOT valid JSON:
browsers' JSON.parse() throws on them, so a single NaN anywhere in a data
file silently breaks whichever dashboard tab reads that file (this has bitten
the "current price" column and the Day Trading tab before).

Use dump()/dumps() here instead of json.dump()/json.dumps() for anything
written to data/ or embedded in the dashboard. Non-finite numbers become
null (the honest "value could not be computed" marker the JS already treats
as missing). Anything _clean() doesn't recognise is passed through untouched,
so this is a safe drop-in -- worst case it behaves exactly like json.
"""
import json
import math


def _clean(obj):
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    # numpy scalars (float64/int64) expose .item(); normalise then re-check
    item = getattr(obj, "item", None)
    if callable(item):
        try:
            return _clean(item())
        except (ValueError, TypeError):
            return obj
    return obj


def dumps(obj, **kw):
    return json.dumps(_clean(obj), **kw)


def dump(obj, fp, **kw):
    json.dump(_clean(obj), fp, **kw)
