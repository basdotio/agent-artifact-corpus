"""The user's rule. Edit only LOOKBACK and the body of signal().

window holds the LOOKBACK most recent CLOSED bars, oldest first, and nothing later:
  window.ts, window.open, window.high, window.low, window.close, window.volume
are sequences of exactly LOOKBACK numbers; window.close[-1] is the last closed bar's close.
params is the dict declared under idea.params (grid values are filled in per cell).
Return +1 to enter long, -1 to enter short, 0 to do nothing. The entry is the open of the
next bar. Use nothing but the two arguments: no files, no globals, no clock.

This file is ordinary Python. declare.py check, events.py and sweep.py run it on your machine, and
it is not sandboxed: read it before the first check. The scripts refuse a rule file whose top level
does anything but set constants and define functions, or that imports anything but math and
statistics, or that names open, exec, eval, compile, input or __import__.
"""
LOOKBACK = None  # number of bars the rule needs


def signal(window, params):
    raise NotImplementedError("write the user's rule here, from the user's own words")
