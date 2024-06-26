from dataclasses import dataclass

from traces_parser.parser.environment.call_context import CallContext
from traces_parser.parser.storage.address_key_storage import AddressKeyStorage
from traces_parser.parser.storage.balances import Balances
from traces_parser.parser.storage.last_executed_sub_context import (
    LastExecutedSubContextStorage,
)
from traces_parser.parser.storage.memory import Memory
from traces_parser.parser.storage.stack import Stack
from traces_parser.parser.storage.storage import (
    ContextSpecificStorage,
    RevertableStorage,
    Storage,
)
from traces_parser.datatypes.hexstring import HexString


class ParsingEnvironment:
    def __init__(self, root_call_context: CallContext) -> None:
        self.current_call_context = root_call_context
        self.current_step_index = 0
        self._stack_storage = ContextSpecificStorage(Stack)
        self._memory_storage = ContextSpecificStorage(Memory)
        self._balances_storage = RevertableStorage(Balances())
        self._transient_storage = RevertableStorage(AddressKeyStorage())
        self._persistent_storage = RevertableStorage(AddressKeyStorage())
        self._last_executed_sub_context = LastExecutedSubContextStorage()

    def on_call_enter(self, next_call_context: CallContext):
        for storage in self._storages():
            storage.on_call_enter(self.current_call_context, next_call_context)
        self.current_call_context = next_call_context

    def on_call_exit(self, next_call_context: CallContext):
        for storage in self._storages():
            storage.on_call_exit(self.current_call_context, next_call_context)
        self.current_call_context = next_call_context

    def on_revert(self, next_call_context: CallContext):
        for storage in self._storages():
            storage.on_revert(self.current_call_context, next_call_context)
        self.current_call_context = next_call_context

    def _storages(self) -> list[Storage]:
        return [
            self._last_executed_sub_context,
            self._stack_storage,
            self._memory_storage,
            self._balances_storage,
            self._persistent_storage,
            self._transient_storage,
        ]

    @property
    def stack(self) -> Stack:
        return self._stack_storage.current()

    @property
    def memory(self) -> Memory:
        return self._memory_storage.current()

    @property
    def balances(self) -> Balances:
        return self._balances_storage.current()

    @property
    def transient_storage(self) -> AddressKeyStorage:
        return self._transient_storage.current()

    @property
    def persistent_storage(self) -> AddressKeyStorage:
        return self._persistent_storage.current()

    @property
    def last_executed_sub_context(self) -> CallContext | None:
        return self._last_executed_sub_context.current()


@dataclass
class InstructionOutputOracle:
    """Output data we know from the trace. Oracle, because we can peek one step into the future with this"""

    stack: list[HexString]
    memory: HexString
    depth: int | None
