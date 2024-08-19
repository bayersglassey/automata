from string import ascii_letters
from typing import List, Tuple, Dict, Iterable, Optional, Union, Protocol, NamedTuple
from collections import UserDict


Value = Union['Lambda', 'Variable', 'Application', 'Combinator']
CombinatorBody = Union[int, List['CombinatorBody']]


class Value(Protocol):

    def __call__(self, *args: Value) -> Value:
        raise NotImplementedError

    def __str__(self) -> str:
        raise NotImplementedError

    def replace(self, values: Dict[str, Value]) -> Value:
        raise NotImplementedError


class Lambda(NamedTuple):
    """

        >>> f = Lambda('xy', Variable('x'))
        >>> print(f)
        (/xy.x)
        >>> print(f(Variable('a')))
        ((/xy.x)a)
        >>> print(f(Variable('a'), Variable('b')))
        a
        >>> print(f(Variable('a'), Variable('b'), Variable('c')))
        (ac)

        >>> f = Lambda('xyz',
        ...     Application(Variable('x'), (
        ...         Variable('z'),
        ...         Application(Variable('y'), (
        ...             Variable('z'),
        ...         )),
        ...     )),
        ... )
        >>> print(f)
        (/xyz.(xz(yz)))
        >>> print(f(Variable('a'), Variable('b'), Variable('c')))
        (ac(bc))

    """

    varnames: str
    body: Value

    def __call__(self, *args: Value) -> Value:
        n_args = len(args)
        n_vars = len(self.varnames)
        if n_args < n_vars:
            return Application(self, args)
        elif n_args == n_vars:
            values = dict(zip(self.varnames, args))
            return self.body.replace(values)
        else:
            result = self(*args[:n_vars])
            return Application(result, args[n_vars:])

    def __str__(self) -> str:
        return f'(/{self.varnames}.{self.body.__str__()})'

    def replace(self, values: Dict[str, Value]) -> Value:
        for var in values:
            if var in self.varnames:
                values = {var: value for var, value in values.items()
                    if var not in self.varnames}
                break
        if not values:
            return self
        return Lambda(self.varnames, self.body.replace(values))


class Variable(NamedTuple):
    varname: str

    def __call__(self, *args: Value) -> Value:
        return Application(self, args)

    def __str__(self) -> str:
        return self.varname

    def replace(self, values: Dict[str, Value]) -> Value:
        return values.get(self.varname, self)


class Application(NamedTuple):
    func: Value
    args: Tuple[Value, ...]

    def __call__(self, *args: Value) -> Value:
        return self.func(*(self.args + args))

    def __str__(self) -> str:
        return f'({self.func}{"".join(str(a) for a in self.args)})'

    def replace(self, values: Dict[str, Value]) -> Value:
        return Application(
            self.func.replace(values),
            tuple(a.replace(values) for a in self.args))


class Combinator(NamedTuple):
    """

        >>> print(S(Variable('a'), Variable('b'), Variable('c')))
        (ac(bc))
        >>> print(K(Variable('a'), Variable('b')))
        a
        >>> print(I(Variable('a')))
        a

    """

    name: str
    n_args: int
    body: CombinatorBody

    def __call__(self, *args: Value) -> Value:
        n_args = len(args)
        if n_args < self.n_args:
            return Application(self, args)
        elif n_args == self.n_args:
            def expand(body: CombinatorBody) -> Value:
                if isinstance(body, int):
                    return args[body]
                expanded = [expand(b) for b in body]
                func = expanded[0]
                return func(*expanded[1:])
            return expand(self.body)
        else:
            result = self(*args[:self.n_args])
            return Application(result, args[self.n_args:])

    def __str__(self) -> str:
        return self.name

    def replace(self, values: Dict[str, Value]) -> Value:
        return self


class CombinatorBasis(UserDict):

    def __init__(self, *combinators: Combinator):
        UserDict.__init__(self)
        for c in combinators:
            self[c.name] = c


S = Combinator('S', 3, [0, 2, [1, 2]])
K = Combinator('K', 2, 0)
I = Combinator('I', 1, 0)
SKI = CombinatorBasis(S, K, I)

B = Combinator('B', 3, [0, [1, 2]])
C = Combinator('C', 3, [0, 1, 2])
W = Combinator('W', 2, [0, 1, 1])
BCKW = CombinatorBasis(B, C, K, W)

BIG_BASIS = CombinatorBasis(B, C, I, K, S, W)


class ParseError(Exception):
    pass


class ParseFrame(NamedTuple):

    # 'apply' or 'lambda'
    kind: str

    terms: List[Value]

    # Only used when kind == 'lambda'
    varnames: Optional[str] = None


def parse(
        text: str,
        *,
        basis: Optional[CombinatorBasis] = BIG_BASIS,
        debug: bool = False,
        ) -> Value:
    """

        >>> parse('')
        Traceback (most recent call last):
         ...
        combinators.ParseError: Syntax error: empty expression

        >>> print(parse('x'))
        x

        >>> print(parse('(x)'))
        x

        >>> print(parse('xy'))
        (xy)

        >>> print(parse('(xy)'))
        (xy)

        >>> print(parse('xyz'))
        (xyz)

        >>> print(parse('(xy)z'))
        (xyz)

        >>> print(parse('x(yz)'))
        (x(yz))

        >>> print(parse('/x.y'))
        (/x.y)

        >>> print(parse('/x.yz'))
        (/x.(yz))

        >>> print(parse('f/x.y'))
        (f(/x.y))

        >>> print(parse('/xyz.xz(yz)'))
        (/xyz.(xz(yz)))

        >>> print(parse('(/xyz.xz(yz))x'))
        ((/xyz.(xz(yz)))x)

    """

    stack: List[ParseFrame] = []
    terms: List[Value] = []

    def from_terms() -> Value:
        if not terms:
            raise ParseError("Syntax error: empty expression")
        elif len(terms) == 1:
            return terms[0]
        else:
            func = terms[0]
            args = tuple(terms[1:])
            if isinstance(func, Application):
                return Application(func.func, func.args + args)
            else:
                return Application(func, args)

    def push(kind: str, varnames: Optional[str] = None):
        nonlocal terms
        if debug:
            print(f"PUSH: {kind!r} (stack: {stack!r})")
        stack.append(ParseFrame(kind, terms, varnames))
        terms = []

    def pop():
        nonlocal terms
        if debug:
            print(f"POP (stack: {stack!r})")
        item = from_terms()
        kind, terms, varnames = stack.pop()
        if kind == 'lambda':
            item = Lambda(varnames, item)
        terms.append(item)

    def drain_lambdas_from_stack():
        while stack and stack[-1][0] == 'lambda':
            pop()

    it = iter(text)
    for c in it:
        if debug:
            print(f"GOT: {c!r} (stack: {stack!r})")
        if c in ' \n':
            # Whitespace
            continue
        elif c == '#':
            # Comments
            while True:
                c2 = next(it, None)
                if c2 is None or c2 == '\n':
                    break
        elif c == '(':
            push('apply')
        elif c == ')':
            drain_lambdas_from_stack()
            if not stack:
                raise ParseError("Unexpected ')'")
            pop()
        elif c == '/':
            varnames = []
            while True:
                varname = next(it, None)
                if varname == '.':
                    break
                if varname in ascii_letters:
                    varnames.append(varname)
                else:
                    raise ParseError("Expected variable name(s) after '/', followed by '.'")
            push('lambda', ''.join(varnames))
        elif c in ascii_letters:
            if c.islower():
                terms.append(Variable(c))
            else:
                if basis is None or c not in basis:
                    raise ParseError(f"No combinator {c!r}")
                terms.append(basis[c])
        else:
            raise ParseError(f"Syntax error: invalid character {c!r}")
    drain_lambdas_from_stack()
    if stack:
        raise ParseError(f"Missing {len(stack)} ')' characters")
    return from_terms()
