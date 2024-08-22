import re
import string
from random import random
from automata import *
from itertools import islice
from time import sleep

sys = ElementaryCellularAutomaton(54)
pad0 = lambda s, i: '0' * i + s + '0' * i
P = re.compile(r'(0+|1+)')


CHARS = ' 123456789' + string.ascii_letters
def get_char(i):
    return CHARS[i] if i < len(CHARS) else '#'


def randtape(size, p=.5):
    return ''.join('01'[random() < p] for i in range(size))


def mktapes(tape0, n=100, pad=True, forever=False):
    if pad:
        tape0 = pad0(tape0, n)
    state = sys(tape0, max_iters=0 if forever else n)
    return iter(state) if forever else list(islice(state, n))


def chunkify(stuff, size):
    it = iter(stuff)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk


get_runs = lambda tape: [len(s) for s in P.findall(tape)]


def from_bin(stuff):
    """Could be used as get_i, instead of sum"""
    i = 0
    for x in stuff:
        i = (i << 1) + x
    return i


def render_runs(tapes, *, get_char=get_char):
    for y, tape in enumerate(tapes):
        if y == 0:
            print(f"Tape 0: {tape}")
        runs = get_runs(tape)
        print('[' + ''.join(get_char(i) for i in runs) + ']')


FILTERS_54 = '1110\n0001\n1011\n0100'
def render_tapes(
        tapes,
        *,
        size=1,
        get_char=get_char,
        get_i=sum,
        filters='',
        filter_x=0,
        filter_y=0,
        end=None,
        t=0,
        anim=False,
        ):
    if anim:
        t = t or .1
        end = '\r' if end is None else end
    if isinstance(filters, str):
        # E.g. '1110' -> [1, 1, 1, 0]
        filters = [[1 if c == '1' else 0 for c in filter]
            for filter in filters.splitlines()]
    for y, tape in enumerate(tapes):
        if y == 0:
            print(f"Tape 0: {tape}")
        bb = (1 if c == '1' else 0 for c in tape)
        if filters:
            filter = filters[(filter_y + y) % len(filters)]
            filter_len = len(filter)
            bb = (b ^ filter[(filter_x + x) % filter_len] for x, b in enumerate(bb))
        ii = (get_i(chunk) for chunk in chunkify(bb, size))
        print('[' + ''.join(get_char(i) for i in ii) + ']', end=end)
        if t:
            sleep(t)
