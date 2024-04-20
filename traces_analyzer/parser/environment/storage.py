from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Generic, TypeVar

from typing_extensions import override


class StorageKey(ABC):
    pass


class StorageValue(ABC):
    pass


Key = TypeVar("Key", bound=StorageKey)
Value = TypeVar("Value", bound=StorageValue)


class Storage(ABC, Generic[Key, Value]):
    """
    Types of storage:
    - stack, memory => current call context as key (or stack based)
    - persistent/transient storage => address as key
    - balance, code => address as key
    - calldata, call value, return data => current or previous call context as a key
    """

    def on_call_enter(self):
        pass

    def on_call_exit(self):
        pass

    @abstractmethod
    def get(self, key: Key) -> Value:
        pass


@dataclass
class StackIndexes(StorageKey):
    indexes: Iterable[int]


@dataclass
class StackValue(StorageValue):
    values: list[str]


class StackStorage(Storage[StackIndexes, StackValue]):
    def __init__(self) -> None:
        super().__init__()
        self.stacks: list[list[str]] = [[]]

    @override
    def on_call_enter(self):
        super().on_call_enter()
        self.stacks.append([])

    @override
    def on_call_exit(self):
        super().on_call_exit()
        self.stacks.pop()

    @override
    def get(self, key: StackIndexes) -> StackValue:
        stack = self.current_stack()
        values = [stack[-index] for index in key.indexes]
        return StackValue(values)

    def push(self, value: StackValue):
        """Push all values. Last value will be the top of the stack"""
        self.current_stack().extend(value.values)

    def pop_n(self, n: int):
        """Pop and return the top n stack items"""
        results = self.get(StackIndexes(indexes=range(n)))
        del self.current_stack()[-n:]
        return results

    def clear(self):
        self.stacks[-1] = []

    def current_stack(self) -> list[str]:
        return self.stacks[-1]


@dataclass
class MemoryRange(StorageKey):
    offset: int
    size: int


@dataclass
class MemoryValue(StorageValue):
    value: str


class MemoryStorage(Storage[MemoryRange, MemoryValue]):
    def __init__(self) -> None:
        super().__init__()
        self.memory_stack: list[str] = [""]

    @override
    def on_call_enter(self):
        super().on_call_enter()
        self.memory_stack.append("")

    @override
    def on_call_exit(self):
        super().on_call_exit()
        self.memory_stack.pop()

    def current_memory(self) -> str:
        return self.memory_stack[-1]

    @override
    def get(self, key: MemoryRange) -> MemoryValue:
        memory = self.current_memory()
        offset = key.offset * 2
        to = offset + (key.size * 2)
        if offset < 0 or offset >= len(memory) or to < 0 or to >= len(memory):
            raise Exception(
                f"Memory range goes outside of memory. Tried to access memory[{offset/2}:{to/2}] "
                f"but memory has size {len(memory)/2}."
            )
        return MemoryValue(self.current_memory()[offset:to])

    def get_all(self) -> MemoryValue:
        return MemoryValue(self.current_memory())

    def set(self, offset: int, value: MemoryValue):
        data = value.value
        self.memory_stack[-1] = self.memory_stack[-1][:offset] + data + self.memory_stack[-1][offset + len(data) + 1 :]
