from typing import Sequence

from traces_parser.parser.information_flow.constant_step_indexes import (
    SPECIAL_STEP_INDEXES,
)
from traces_parser.datatypes.storage_byte_group import StorageByteGroup
from traces_parser.datatypes.hexstring import HexString


class Stack:
    def __init__(self) -> None:
        self._stack: list[StorageByteGroup] = []

    def peek(self, index: int) -> StorageByteGroup:
        """Get the nth element from the top of the stack (0-indexed)"""
        return self._stack[-index - 1]

    def push(self, value: StorageByteGroup):
        """Push a single value to the top of the stack"""
        if len(value) < 32:
            raise Exception(f"Invalid size for stack push: {len(value)}")
            padding = StorageByteGroup.from_hexstring(
                HexString.zeros(32 - len(value)),
                SPECIAL_STEP_INDEXES.DEPRECATED,
            )
            value = padding + value
        self._stack.append(value)

    def push_all(self, values: Sequence[StorageByteGroup]):
        """Push multiple values. First one will be on top of the stack"""
        for value in reversed(values):
            self.push(value)

    def get_all(self) -> Sequence[StorageByteGroup]:
        """Get all values. First one will be the top of the stack"""
        return [self.peek(i) for i in range(self.size())]

    def pop(self) -> StorageByteGroup:
        result = self.peek(0)
        self._stack.pop()
        return result

    def set(self, index: int, value: StorageByteGroup):
        if len(value) != 32:
            raise Exception(
                f"Tried to set stack value with unexpected size {len(value)} instead of 32: {value}"
            )
        self._stack[-index - 1] = value

    def clear(self):
        self._stack = []

    def size(self):
        return len(self._stack)
