import os
import re
import traceback
from typing import List, Dict, Tuple, Set, Union, Type
from functools import cached_property

from dataclasses import dataclass


NAME_REGEX = re.compile(r'[a-zA-Z0-9_]')
is_name = NAME_REGEX.match

TWO_BYTE_INSTRUCTIONS = ('=', '.', '=.', '@', ':', "'")

Instruction = Union[str, int]
Value = Union[str, Dict[str, 'Value'], 'Func']
Vars = Dict[str, Value]
Stack = List[Value]
Dumped = Dict[int, int]


def dumps(value: Value, depth: int = 0, dumped: Dumped = None) -> str:
    if isinstance(value, str):
        return f"'{value}"

    if dumped is None:
        dumped = {}
    if id(value) in dumped:
        return f'${dumped[id(value)]};'
    dump_index = len(dumped)
    dumped[id(value)] = dump_index

    if isinstance(value, dict):
        s = '[=o'
        for k, v in value.items():
            s += f'{dumps(v, depth + 1, dumped)}o=.{k}'
        s += ']*!'
    elif isinstance(value, Func):
        s = '['
        for k, v in value.vars.items():
            s += f'{dumps(v, depth + 1, dumped)}={k}'
        for v in value.stack:
            s += dumps(v, depth + 1, dumped)
        s += str(value.code)
        s += ']'
    else:
        raise TypeError(type(value))
    s += f'=${dump_index};'
    return s


class BadSyntax(Exception):
    def __init__(self, msg: str, text: str, text_i: int):
        self.msg = msg
        self.text = text
        self.text_i = text_i

    def __str__(self):
        return f"{self.msg} (text={self.text!r} text_i={self.text_i!r})"


class IncompleteSyntax(BadSyntax): pass


class RunError(Exception):
    def __init__(
            self,
            msg: str,
            code: 'Code',
            vars: Vars,
            stack: Stack,
            code_i: int,
            ):
        self.msg = msg
        self.code = code
        self.vars = vars
        self.stack = stack
        self.code_i = code_i

    def __str__(self):
        text_i = self.code.get_text_i(self.code_i)
        return f"{self.msg} (text={self.code.text!r} text_i={text_i} vars={self.vars!r} stack={self.stack!r})"


class Code:

    def __init__(self, text: str):
        instructions: List[Instruction] = []
        labels: Dict[str, int] = {}
        children: List[Code] = []
        code_i_to_text_i: Dict[int, int] = {}
        text_i = 0
        def error(msg: str, cls: Type[BadSyntax] = BadSyntax):
            raise cls(msg, text, text_i)
        def getchar():
            nonlocal text_i
            while text_i < len(text):
                yield text[text_i]
                text_i += 1
        it = getchar()
        for c in it:
            text_i_start_of_instruction = text_i
            def add_instruction(c: Instruction):
                code_i = len(instructions)
                code_i_to_text_i[code_i] = text_i_start_of_instruction
                instructions.append(c)
            if c in ' \n(){};':
                # Whitespace
                pass
            elif c == '#':
                # Comment
                while c != '\n':
                    c = next(it, '\n')
            elif c in '*!^/?' or is_name(c):
                add_instruction(c)
            elif c in ".@'":
                c0 = c
                c = next(it, '')
                if not is_name(c):
                    error(f"Expected a name after {c0!r}, got: {c!r}")
                add_instruction(c0)
                add_instruction(c)
            elif c == ':':
                c = next(it, '')
                if not is_name(c):
                    error(f"Expected a name after ':', got: {c!r}")
                if c in labels:
                    error(f"Duplicate label: {c!r}")
                labels[c] = len(instructions)
            elif c == '=':
                c = next(it, '')
                if c == '.':
                    c = next(it, '')
                    if not is_name(c):
                        error(f"Expected a name after '=.', got: {c!r}")
                    add_instruction('=.')
                    add_instruction(c)
                else:
                    if not is_name(c):
                        error(f"Expected a name after '=', got: {c!r}")
                    add_instruction('=')
                    add_instruction(c)
            elif c == '[':
                i0 = text_i + 1
                depth = 1
                while depth:
                    c = next(it, '')
                    if not c:
                        error(f"Missing terminating ']'", IncompleteSyntax)
                    if c == '[':
                        depth += 1
                    elif c == ']':
                        depth -= 1
                child = Code(text[i0:text_i])
                add_instruction('[]')
                add_instruction(len(children))
                children.append(child)
            else:
                error(f"Unknown instruction: {c!r}")

        self.text = text
        self.instructions = instructions
        self.labels = labels
        self.children = children
        self.code_i_to_text_i = code_i_to_text_i

    def __str__(self):
        return self.text

    def __repr__(self):
        return f'{self.__class__.__name__}({self.text!r})'

    def get_text_i(self, code_i: int) -> int:
        if code_i >= len(self.instructions):
            return len(self.text)
        return self.code_i_to_text_i.get(code_i)

    @cached_property
    def assigned_vars(self) -> Set[str]:
        vars = set()
        it = iter(self.instructions)
        for c in it:
            if c == '=':
                c = next(it)
                vars.add(c)
        return vars

    @cached_property
    def free_vars(self) -> Set[str]:
        vars = set()
        it = iter(self.instructions)
        for c in it:
            if c in TWO_BYTE_INSTRUCTIONS:
                next(it)
            elif isinstance(c, str) and is_name(c):
                vars.add(c)
        for child in self.children:
            vars.update(child.free_vars)
        return vars - self.assigned_vars

    def __call__(
            self,
            vars: Vars = None,
            stack: Stack = None,
            code_i: int = 0,
            debug: bool = False,
            ) -> Tuple[Vars, Stack, int]:
        vars = {} if vars is None else vars
        stack = [] if stack is None else stack
        instructions = self.instructions
        def error(msg: str):
            raise RunError(msg, self, vars, stack, code_i)
        def iter_instructions():
            nonlocal code_i
            while code_i < len(instructions):
                yield instructions[code_i]
                code_i += 1
        def pop():
            if not stack:
                error("Stack empty")
            return stack.pop()
        it = iter_instructions()
        def debug_print(msg):
            print(f"{msg} (code_i={code_i} stacklen={len(stack)} vars={''.join(vars)!r})")
        try:
            for c in it:
                if debug:
                    debug_print(f"RUN: {'v' if is_name(c) else c}")
                if c == '*':
                    stack.append({})
                elif c == '^':
                    pop()
                elif c == '@':
                    c = next(it)
                    code_i = self.labels[c] - 1
                elif c == "'":
                    c = next(it)
                    stack.append(c)
                elif c in '?/':
                    x = pop()
                    y = pop()
                    if (x == y) ^ (c == '?'):
                        c = next(it)
                        if c in TWO_BYTE_INSTRUCTIONS:
                            c = next(it)
                elif c == '.':
                    c = next(it)
                    o = pop()
                    stack.append(o[c])
                elif c == '=':
                    c = next(it)
                    vars[c] = pop()
                elif c == '=.':
                    c = next(it)
                    o = pop()
                    x = pop()
                    o[c] = x
                elif c == '[]':
                    c = next(it)
                    f_code = self.children[c]
                    f = Func(
                        code=f_code,
                        vars={k: vars[k] for k in f_code.free_vars},
                        stack=[],
                        code_i=0,
                    )
                    stack.append(f)
                elif c == '!':
                    x = pop()
                    f = pop()
                    stack.append(f(x, debug))
                elif isinstance(c, str) and is_name(c):
                    stack.append(vars[c])
                else:
                    error(f"Unknown instruction: {c!r}")
        except Exception as ex:
            if isinstance(ex, RunError):
                raise
            error("Whoops.")
        if debug:
            debug_print("RETURN")
        return vars, stack, code_i


class Func:

    def __init__(
            self,
            code: Code,
            vars: Vars,
            stack: Stack,
            code_i: int,
            ):
        self.code = code
        self.vars = vars
        self.stack = stack
        self.code_i = code_i

    def __str__(self):
        return f"[{self.code}] (stack: {len(self.stack)}, code_i: {self.code_i})"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.code!r}, {self.vars!r}, {self.stack!r}, {self.code_i})"

    @staticmethod
    def parse(text: str, vars: Vars = None, stack: Stack = None, code_i: int = 0) -> 'Func':
        code = Code(text)
        vars = {} if vars is None else vars
        stack = [] if stack is None else stack
        return Func(code, vars, stack, code_i)

    def __call__(self, arg: Value, debug: bool = False) -> Value:
        vars = self.vars.copy()
        stack = self.stack + [arg]
        vars, stack, code_i = self.code(vars, stack, self.code_i, debug)
        if len(stack) != 1:
            raise RunError(f"On function return, stack size should be 1, but was: {len(stack)}",
                self.code, vars, stack, code_i)
        return stack[0]


def main():
    debug = os.environ.get('DEBUG', '').upper() in ('1', 'TRUE')
    vars = {}
    stack = []
    def print_special_commands():
        print(f"Special commands: '%exit' '%info' '%debug'")
    print_special_commands()
    prev_text = ''
    while True:
        text = input('- ' if prev_text else '> ')
        if not text:
            continue
        if text.startswith('%'):
            if text in ('%exit', '%e'):
                break
            elif text in ('%debug', '%d'):
                debug = not debug
                print(f"Debug mode: {'ON' if debug else 'OFF'}")
            elif text in ('%info', '%i'):
                dumped = {}
                vars_lines = []
                stack_lines = []
                for k, v in vars.items():
                    vars_lines.append(f" {k}: {dumps(v, 0, dumped)}")
                for i, v in enumerate(reversed(stack)):
                    stack_lines.append(f" {i}: {dumps(v, 0, dumped)}")
                print(f"Vars:")
                for line in vars_lines:
                    print(line)
                print(f"Stack:")
                for line in stack_lines:
                    print(line)
            else:
                print(f"Unknown special command: {text}")
                print_special_commands()
            continue

        text = prev_text + text
        prev_text = ''

        try:
            code = Code(text)
            vars, stack, code_i = code(vars, stack, debug=debug)
        except IncompleteSyntax as ex:
            prev_text = ex.text + '\n'
        except Exception as ex:
            traceback.print_exc()
        except KeyboardInterrupt:
            print(f"Enter the command '%exit' to exit.")


if __name__ == '__main__':
    main()
