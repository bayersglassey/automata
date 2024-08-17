
from typing import List, Dict
from dataclasses import dataclass
from random import choice


@dataclass
class BaseTagSystemState:
    system: 'BaseTagSystem'
    tape: str
    max_iters: int = 100

    __iter__ = lambda self: self

    def __post_init__(self):
        self.iters = -1

    def __next__(self) -> str:
        self.iters += 1
        if self.iters == 0:
            # Always yield the initial tape value
            return self.tape
        if self.iters > self.max_iters:
            raise Exception(f"Exceeded max iterations: {self.max_iters}")
        tape = self.step()
        self.tape = tape
        return tape

    def step(self) -> str:
        raise NotImplementedError


class BaseTagSystem:
    def __post_init__(self):
        pass

    def __call__(self, tape: str, **kwargs) -> BaseTagSystemState:
        raise NotImplementedError


@dataclass
class TagSystemState(BaseTagSystemState):
    system: 'TagSystem'

    def step(self) -> str:
        system = self.system
        tape = self.tape

        if len(tape) < system.deletion_number:
            raise StopIteration
        symbol = tape[0]
        if symbol == system.halting_symbol:
            raise StopIteration

        production = system.productions[symbol]
        return tape[system.deletion_number:] + production


@dataclass
class TagSystem(BaseTagSystem):
    """

        >>> sys = TagSystem(2, {'a':'ccbaH','b':'cca','c':'cc'}, 'H')
        >>> list(sys('baa'))
        ['baa', 'acca', 'caccbaH', 'ccbaHcc', 'baHcccc', 'Hcccccca']

    """

    deletion_number: int
    productions: Dict[str, str]
    halting_symbol: str = ''

    def __post_init__(self):
        super().__post_init__()

        # Validate productions
        if not self.productions:
            raise Exception("No productions")
        bad_lens = {s for s in self.productions if len(s) != 1}
        if bad_lens:
            raise Exception(f"Productions given with \"symbols\" whose len != 1: {bad_lens!r}")
        all_syms = set()
        for production in self.productions.values():
            all_syms.update(production)
        if self.halting_symbol:
            all_syms -= {self.halting_symbol}
        missing_syms = all_syms - set(self.productions)
        if missing_syms:
            raise Exception(f"Missing productions for symbols: {missing_syms!r}")

        # Validate halting symbol
        if len(self.halting_symbol) > 1:
            raise Exception("Halting symbol must be of length <= 1")

    def __call__(self, tape: str, **kwargs) -> TagSystemState:
        extra_syms = set(tape) - set(self.productions)
        if extra_syms:
            raise Exception(f"Tape contains symbols without productions: {extra_syms!r}")
        return TagSystemState(system=self, tape=tape, **kwargs)


@dataclass
class CyclicTagSystemState(BaseTagSystemState):
    system: 'CyclicTagSystem'

    def __post_init__(self):
        super().__post_init__()
        self.production_i = 0

    def step(self) -> str:
        system = self.system
        tape = self.tape

        if not tape:
            raise StopIteration

        symbol = tape[0]
        tape = tape[1:]
        if symbol == '1':
            tape += system.productions[self.production_i]
        self.production_i = (self.production_i + 1) % len(system.productions)
        return tape


@dataclass
class CyclicTagSystem(BaseTagSystem):
    """

        Based on: https://en.wikipedia.org/wiki/Tag_system
        Specifically, this is a cyclic tag system "emulating" a particular
        2-tag system.
        The emulated system has symbols 'a', 'b', 'H' (halting symbol).
        They are encoded as words '100', '010', and '001' respectively.
        Each 6 steps of the cyclic tag system represent one step of the
        emulated system.
        On each 6th step, we must check the start of the tape for the
        encoded halting symbol, '001'.
        >>> sys = CyclicTagSystem(['010010', '100010001', '001', '', '', ''])
        >>> for i, tape in enumerate(sys('010100')):
        ...     print(('* ' if i % 6 == 0 else '  ') + tape)
        ...     if i % 6 == 0 and tape.startswith('001'):
        ...         break
        * 010100
          10100
          0100100010001
          100100010001
          00100010001
          0100010001
        * 100010001
          00010001010010
          0010001010010
          010001010010
          10001010010
          0001010010
        * 001010010

    """

    # Each production should be a string consisting only of the
    # symbols '0' and '1'
    productions: List[str]

    def __post_init__(self):
        super().__post_init__()

        # Validate productions
        if not self.productions:
            raise Exception("No productions")
        extra_symbols = {
            production for production in self.productions
            if set(production) - {'0', '1'}}
        if extra_symbols:
            raise Exception(f"Productions contain symbols other than '0' and '1': {extra_symbols!r}")

    def __call__(self, tape: str, **kwargs) -> CyclicTagSystemState:
        extra_syms = set(tape) - {'0', '1'}
        if extra_syms:
            raise Exception(f"Tape contains symbols other than '0' and '1': {extra_syms!r}")
        return CyclicTagSystemState(system=self, tape=tape, **kwargs)


@dataclass
class SemiThueSystemState(BaseTagSystemState):
    system: 'SemiThueSystem'

    def step(self) -> str:
        system = self.system
        tape = self.tape

        if system.is_random:
            # Apply a random matching rule
            matching_rules = [(from_word, to_word)
                for from_word, to_word in system.rules.items()
                if from_word in tape]
            from_word, to_word = choice(matching_rules)
            return tape.replace(from_word, to_word)
        else:
            # Apply the first matching rule
            for in_word, out_word in system.rules.items():
                if in_word in tape:
                    return tape.replace(in_word, out_word)

        # No rules applied
        raise StopIteration


@dataclass
class SemiThueSystem(BaseTagSystem):
    """

        >>> sys = SemiThueSystem({
        ...     '^o': 'i^',
        ...     '^b': 'b^',
        ...     '^d': 'd^',
        ...     '^g': 'g^',
        ...     '^ ': ' ^',
        ...     '^': '',
        ... })
        >>> for tape in sys('^dog bog'): print(tape)
        ^dog bog
        d^og bog
        di^g bog
        dig^ bog
        dig ^bog
        dig b^og
        dig bi^g
        dig big^
        dig big

    """

    rules: Dict[str, str]
    is_random: bool = False

    def __call__(self, tape: str, **kwargs) -> SemiThueSystemState:
        return SemiThueSystemState(system=self, tape=tape, **kwargs)


@dataclass
class ElementaryCellularAutomatonState(BaseTagSystemState):
    system: 'ElementaryCellularAutomatonState'

    def step(self) -> str:
        system = self.system
        tape = self.tape
        if not tape:
            return tape

        cells = [int(c == '1') for c in tape]

        # Add first cell to the back, and last cell to the front
        # (so new_cells doesn't have to do modular arithmetic)
        cells.insert(0, cells[-1])
        cells.append(cells[1])

        new_cells = [
            system.apply_rule(cells[i-1], cells[i], cells[i+1])
            for i in range(1, len(cells) - 1)]
        return ''.join('1' if cell else '0' for cell in new_cells)


@dataclass
class ElementaryCellularAutomaton(BaseTagSystem):
    """

        >>> from itertools import islice
        >>> pad = lambda s, i: '0' * i + s + '0' * i

        >>> sys = ElementaryCellularAutomaton(54)
        >>> for tape in islice(sys(pad('1101', 10)), 10): print(tape)
        000000000011010000000000
        000000000100111000000000
        000000001111000100000000
        000000010000101110000000
        000000111001110001000000
        000001000110001011100000
        000011101001011100010000
        000100011111100010111000
        001110100000010111000100
        010001110000111000101110

    """

    rule_no: int = 0

    def apply_rule(self, c0: int, c1: int, c2: int) -> int:
        n = (c0 << 2) + (c1 << 1) + (c2 << 0)
        return self.rule_no & (1 << n)

    def __call__(self, tape: str, **kwargs) -> SemiThueSystemState:
        extra_syms = set(tape) - {'0', '1'}
        if extra_syms:
            raise Exception(f"Tape contains symbols other than '0' and '1': {extra_syms!r}")
        return ElementaryCellularAutomatonState(system=self, tape=tape, **kwargs)
