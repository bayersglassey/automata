
Implementations of various automata and rewriting systems in Python.

For automata.py, see:
* https://arxiv.org/pdf/0906.3248
* https://en.wikipedia.org/wiki/Tag_system
* https://en.wikipedia.org/wiki/Semi-Thue_system

For combinators.py, see:
* https://en.wikipedia.org/wiki/Lambda_calculus
* https://en.wikipedia.org/wiki/Combinatory_logic
* https://en.wikipedia.org/wiki/SKI_combinator_calculus


## Examples

### Lambda Calculus & Combinators

```python
>>> from combinators import parse

Create a Lambda object
>>> f = parse('/xyz.xz(yz)')
>>> type(f)
<class 'combinators.Lambda'>

Let's create some variables to pass to the lambda...
>>> a = parse('a')
>>> b = parse('b')
>>> c = parse('c')

Partial application:
>>> print(f(a))
((/xyz.(xz(yz)))a)

Fully reduced application:
>>> print(f(a, b, c))
(ac(bc))

You can use "replace" to bind variables:
>>> print(parse('fabc').replace(f=f))
((/xyz.(xz(yz)))abc)

Call a function application with no arguments to simplify it:
>>> print(parse('fabc').replace(f=f)())
(ac(bc))
```

```python
>>> from combinators import parse, S, K, I

You can use combinators directly
>>> print(S(K, I))
(SKI)
>>> print(S(K, I, I))
I

You can also parse them, intermingled with lambdas
>>> parse('S') is S
True
>>> print(parse('/x.Kx')(I))
(KI)

Remember, you can call applications with no arguments to simplify them!
>>> print(parse('KISS'))
(KISS)
>>> print(parse('KISS')())
(IS)
>>> print(parse('KISS')()())
S
```

TODO: different reduction strategies, etc.


### Automata


```python
>>> from automata import ElementaryCellularAutomaton
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
```

```python
>>> from automata import SemiThueSystem
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
```

```python
Based on: https://en.wikipedia.org/wiki/Tag_system
Specifically, this is a cyclic tag system "emulating" a particular
2-tag system.
The emulated system has symbols 'a', 'b', 'H' (halting symbol).
They are encoded as words '100', '010', and '001' respectively.
Each 6 steps of the cyclic tag system represent one step of the
emulated system.
On each 6th step, we must check the start of the tape for the
encoded halting symbol, '001'.

>>> from automata import CyclicTagSystem
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
```
