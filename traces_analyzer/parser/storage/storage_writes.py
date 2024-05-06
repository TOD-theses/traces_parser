from abc import ABC
from dataclasses import dataclass
from typing import Iterable, Sequence

from traces_analyzer.parser.storage.storage_value import StorageByteGroup


@dataclass
class StorageWrite(ABC):
    pass


@dataclass
class StorageAccess(ABC):
    pass


@dataclass
class StackAccess(StorageAccess):
    index: int
    value: StorageByteGroup


@dataclass
class StackSet(StorageWrite):
    index: int
    value: StorageByteGroup


@dataclass
class StackPush(StorageWrite):
    value: StorageByteGroup


@dataclass
class StackPop(StorageWrite):
    pass


@dataclass
class MemoryWrite(StorageWrite):
    offset: int
    value: StorageByteGroup


@dataclass
class MemoryAccess(StorageAccess):
    offset: int
    value: StorageByteGroup


@dataclass
class CalldataWrite(StorageWrite):
    value: StorageByteGroup


@dataclass
class ReturnWrite(StorageWrite):
    value: StorageByteGroup


@dataclass
class ReturnDataAccess(StorageAccess):
    offset: int
    size: int
    value: StorageByteGroup


@dataclass
class BalanceAccess(StorageAccess):
    address: StorageByteGroup
    last_modified_step_index: int


@dataclass
class BalanceTransferWrite(StorageWrite):
    address_from: StorageByteGroup
    address_to: StorageByteGroup
    value: StorageByteGroup


@dataclass
class SelfdestructWrite(StorageWrite):
    address_from: StorageByteGroup
    address_to: StorageByteGroup


@dataclass
class StorageWrites:
    stack_sets: Sequence[StackSet] = ()
    stack_pops: Sequence[StackPop] = ()
    stack_pushes: Sequence[StackPush] = ()
    memory: Sequence[MemoryWrite] = ()
    calldata: CalldataWrite | None = None
    return_data: ReturnWrite | None = None
    balance_transfers: Sequence[BalanceTransferWrite] = ()
    selfdestruct: Sequence[SelfdestructWrite] = ()

    @staticmethod
    def merge(writes: list["StorageWrites"]) -> "StorageWrites":
        mem_writes: list[MemoryWrite] = []
        calldata_write: CalldataWrite | None = None
        return_data_write: ReturnWrite | None = None
        stack_sets: list[StackSet] = []
        stack_pops: list[StackPop] = []
        stack_pushes: list[StackPush] = []
        balance_transfers: list[BalanceTransferWrite] = []
        selfdestructs: list[SelfdestructWrite] = []

        for write in writes:
            stack_sets.extend(write.stack_sets)
            stack_pops.extend(write.stack_pops)
            stack_pushes.extend(write.stack_pushes)
            mem_writes.extend(write.memory)
            calldata_write = calldata_write or write.calldata
            return_data_write = return_data_write or write.return_data
            balance_transfers.extend(write.balance_transfers)
            selfdestructs.extend(write.selfdestruct)

        return StorageWrites(
            stack_sets=stack_sets,
            stack_pops=stack_pops,
            stack_pushes=stack_pushes,
            memory=mem_writes,
            calldata=calldata_write,
            return_data=return_data_write,
            balance_transfers=balance_transfers,
            selfdestruct=selfdestructs,
        )


@dataclass
class StorageAccesses:
    stack: Sequence[StackAccess] = ()
    memory: Sequence[MemoryAccess] = ()
    balance: Sequence[BalanceAccess] = ()
    return_data: ReturnDataAccess | None = None

    def get_dependencies(self) -> Iterable[tuple[int, StorageAccess, StorageByteGroup | None]]:
        # TODO: unit test
        for stack_access in self.stack:
            for group in stack_access.value.split_by_dependencies():
                step_index = next(iter(group.depends_on_instruction_indexes()))
                yield (step_index, stack_access, group)

        for memory_access in self.memory:
            for group in memory_access.value.split_by_dependencies():
                step_index = next(iter(group.depends_on_instruction_indexes()))
                yield (step_index, memory_access, group)

        for balance_access in self.balance:
            yield (balance_access.last_modified_step_index, balance_access, None)

        if self.return_data:
            for group in self.return_data.value.split_by_dependencies():
                step_index = next(iter(group.depends_on_instruction_indexes()))
                yield (step_index, self.return_data, group)

    @staticmethod
    def merge(accesses: list["StorageAccesses"]) -> "StorageAccesses":
        memory_accesses: list[MemoryAccess] = []
        stack_accesses: list[StackAccess] = []
        balance_accesses: list[BalanceAccess] = []
        return_data_access: ReturnDataAccess | None = None
        for access in accesses:
            memory_accesses.extend(access.memory)
            stack_accesses.extend(access.stack)
            balance_accesses.extend(access.balance)
            return_data_access = return_data_access or access.return_data

        return StorageAccesses(
            stack=stack_accesses,
            memory=memory_accesses,
            balance=balance_accesses,
            return_data=return_data_access,
        )
