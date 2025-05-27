from typing import List, Optional


def cells_tostr(cells: List[int], just: int = 3) -> str:
    return f"({' '.join(str(cell).rjust(just) for cell in cells)})"


class Tape:

    def __init__(self, cells: List[int], pos: int = 0, no_neg: bool = True):
        self.cells = cells
        self.pos = pos
        self.no_neg = no_neg

    def print(self, *, just: int = 3, file=None):
        print(cells_tostr(self.cells, just), file=file)
        print(' ' + ' ' * ((just + 1) * self.pos) + '^'.rjust(just))

    def get(self) -> int:
        return self.cells[self.pos]

    def add(self, n: int = 1):
        cell = self.cells[self.pos]
        new_cell = cell + n
        if self.no_neg and new_cell < 0:
            raise Exception(f"Cell value would go negative! {cell} + {n} = {new_cell}")
        self.cells[self.pos] = new_cell

    def move(self, n: int):
        self.pos = (self.pos + n) % len(self.cells)


class State:

    def __init__(self, tape: Tape, program: str):
        self.tape = tape
        self.program = program
        self.program_pos = 0

    def get_cmd(self) -> Optional[str]:
        if self.program_pos < len(self.program):
            return self.program[self.program_pos]
        return None

    def print_program(self, *, file=None):
        print(self.program)
        print(' ' * self.program_pos + '^')

    def step(self) -> Optional[str]:
        """Executes 1 step, returning the command which was executed"""
        while True:
            command = self.get_cmd()
            if not command:
                return None
            self.program_pos += 1
            if command == '+':
                self.tape.add(1)
            elif command == '-':
                self.tape.add(-1)
            elif command == '<':
                self.tape.move(-1)
            elif command == '>':
                self.tape.move(1)
            elif command == '[':
                num = self.tape.get()
                if num == 0:
                    self.program_pos -= 1
                    depth = 1
                    while depth > 0:
                        self.program_pos += 1
                        cmd = self.program[self.program_pos]
                        if cmd == '[':
                            depth += 1
                        elif cmd == ']':
                            depth -= 1
                    self.program_pos += 1
            elif command == ']':
                num = self.tape.get()
                if num != 0:
                    self.program_pos -= 1
                    depth = 1
                    while depth > 0:
                        self.program_pos -= 1
                        cmd = self.program[self.program_pos]
                        if cmd == ']':
                            depth += 1
                        elif cmd == '[':
                            depth -= 1
                    self.program_pos += 1
            else:
                continue
            break
        return command


def main():
    tape = Tape([0] * 20)
    prev_program = ''
    tape.print()
    while True:
        try:
            program = prev_program + input(': ' if prev_program else '$ ').strip()
            prev_program = ''
            if not program:
                continue
            n_open = sum(c == '[' for c in program)
            n_close = sum(c == ']' for c in program)
            if n_close > n_open:
                print("Syntax error: too many ']'!")
                continue
            elif n_open > n_close:
                prev_program = program
                continue
            print()
            print('-' * 80)
            tape.print()
            state = State(tape, program)
            while True:
                print("Executing:")
                state.print_program()
                cmd = state.step()
                if not cmd:
                    break
                tape.print()
        except KeyboardInterrupt:
            return
        except Exception as ex:
            print(f"ERROR: {ex}")


if __name__ == '__main__':
    main()
