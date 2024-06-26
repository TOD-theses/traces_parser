from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping, TypedDict

from typing_extensions import override

from traces_parser.parser.environment.call_context import CallContext
from traces_parser.parser.environment.parsing_environment import (
    InstructionOutputOracle,
    ParsingEnvironment,
)
from traces_parser.parser.information_flow.information_flow_dsl import (
    balance_of,
    balance_transfer,
    calldata_range,
    calldata_size,
    calldata_write,
    callvalue,
    combine,
    current_storage_address,
    mem_range,
    mem_size,
    mem_write,
    noop,
    oracle_mem_range_peek,
    oracle_stack_peek,
    persistent_storage_get,
    persistent_storage_set,
    return_data_range,
    return_data_size,
    return_data_write,
    selfdestruct,
    stack_arg,
    stack_peek,
    stack_push,
    stack_set,
    to_size,
    transient_storage_get,
    transient_storage_set,
)
from traces_parser.parser.information_flow.information_flow_spec import FlowSpec
from traces_parser.parser.instructions.instruction import Instruction
from traces_parser.datatypes.storage_byte_group import StorageByteGroup
from traces_parser.parser.storage.storage_writes import (
    MemoryWrite,
    StackPush,
    StorageWrites,
)
from traces_parser.datatypes.hexstring import HexString

CallDataNew = TypedDict(
    "CallDataNew",
    {
        "address": HexString,
        "value": StorageByteGroup,
        "updates_storage_address": bool,
        "input": StorageByteGroup,
    },
)


class CallContextEnteringInstruction(Instruction, ABC):
    def create_call_context(self) -> CallContext:
        return CallContext(
            parent=self.call_context,
            initiating_instruction=self,
            calldata=self.child_input,
            value=self.child_value,
            depth=self.call_context.depth + 1,
            msg_sender=self.child_caller,
            code_address=self.child_code_address,
            storage_address=self.child_storage_address,
            is_contract_initialization=self.child_is_created,
        )

    @property
    @abstractmethod
    def child_code_address(self) -> HexString:
        pass

    @property
    @abstractmethod
    def child_storage_address(self) -> HexString:
        pass

    @property
    @abstractmethod
    def child_value(self) -> StorageByteGroup:
        pass

    @property
    @abstractmethod
    def child_input(self) -> StorageByteGroup:
        pass

    @property
    @abstractmethod
    def child_caller(self) -> HexString:
        pass

    @property
    @abstractmethod
    def child_is_created(self) -> bool:
        pass


class CallInstruction(CallContextEnteringInstruction, ABC):
    @abstractmethod
    def get_return_writes(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> StorageWrites:
        """Writes that occur when a sub-context has exited"""
        pass

    @abstractmethod
    def get_immediate_return_writes(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> StorageWrites:
        """Writes that occur on a call to a precompiled contract or an EOA"""
        pass

    @property
    @override
    def child_is_created(self) -> bool:
        return False


class ContractCreatingInstruction(CallContextEnteringInstruction, ABC):
    @property
    @override
    def child_is_created(self) -> bool:
        return True


@dataclass(frozen=True, repr=False, eq=False)
class CALL(CallInstruction):
    flow_spec = combine(
        stack_arg(0),
        # TODO: ensure that balance transfer is marked as reverted (or something like that)
        # if the call_context did not execute/got reverted (double check specification)
        balance_transfer(current_storage_address(), stack_arg(1), stack_arg(2)),
        calldata_write(mem_range(stack_arg(3), stack_arg(4))),
        # we access the memory for the memory expansion
        # note that the memory expansion always happens
        # even if the actual return data is not that large
        mem_range(stack_arg(5), stack_arg(6)),
    )

    @property
    @override
    def child_code_address(self) -> HexString:
        return self.flow.accesses.stack[1].value.get_hexstring().as_address()

    @property
    @override
    def child_storage_address(self) -> HexString:
        return self.flow.accesses.stack[1].value.get_hexstring().as_address()

    @property
    @override
    def child_value(self) -> StorageByteGroup:
        return self.flow.accesses.stack[2].value

    @property
    @override
    def child_input(self) -> StorageByteGroup:
        assert (
            self.flow.writes.calldata is not None
        ), f"Tried to get CALL data but contains no write for it: {self.flow}"
        return self.flow.writes.calldata.value

    @property
    @override
    def child_caller(self) -> HexString:
        return self.call_context.storage_address

    def get_return_writes(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> StorageWrites:
        assert env.last_executed_sub_context, f"Tried to get call return writes, but did not find last executed sub context: {env}"
        child_context = env.last_executed_sub_context
        _, _, _, _, _, offset_access, size_access = self.flow.accesses.stack
        offset = offset_access.value.get_hexstring().as_int()
        size = size_access.value.get_hexstring().as_int()
        if size == 0:
            mem_writes = []
        else:
            return_data = child_context.return_data
            return_data_slice = return_data[:size]
            # TODO: if actual size is lower than the allowed return size, we still do memory expansion (without overwriting any values inbetween)
            mem_writes = [MemoryWrite(offset, return_data_slice)]
        success = "0x0" if child_context.reverted else "0x1"
        stack_push = StackPush(
            StorageByteGroup.from_hexstring(
                HexString(success).as_size(32), self.step_index
            )
        )
        return StorageWrites(stack_pushes=[stack_push], memory=mem_writes)

    def get_immediate_return_writes(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> StorageWrites:
        _, _, _, _, _, offset_access, size_access = self.flow.accesses.stack
        offset = offset_access.value.get_hexstring().as_int()
        size = size_access.value.get_hexstring().as_int()
        return_data_slice = output_oracle.memory[offset * 2 : (offset + size) * 2]
        success = StorageByteGroup.from_hexstring(
            output_oracle.stack[0],
            self.step_index,
        )
        return StorageWrites(
            stack_pushes=[StackPush(success)],
            memory=[
                MemoryWrite(
                    offset,
                    StorageByteGroup.from_hexstring(return_data_slice, self.step_index),
                )
            ],
        )


@dataclass(frozen=True, repr=False, eq=False)
class STATICCALL(CallInstruction):
    flow_spec = combine(
        stack_arg(0),
        stack_arg(1),
        calldata_write(mem_range(stack_arg(2), stack_arg(3))),
        # memory expansion on return (see CALL)
        mem_range(stack_arg(4), stack_arg(5)),
    )

    @property
    @override
    def child_code_address(self) -> HexString:
        return self.flow.accesses.stack[1].value.get_hexstring().as_address()

    @property
    @override
    def child_storage_address(self) -> HexString:
        return self.flow.accesses.stack[1].value.get_hexstring().as_address()

    @property
    @override
    def child_value(self) -> StorageByteGroup:
        return StorageByteGroup.from_hexstring(HexString.zeros(32), self.step_index)

    @property
    @override
    def child_input(self) -> StorageByteGroup:
        assert (
            self.flow.writes.calldata is not None
        ), f"Tried to get STATICCALL data but contains no write for it: {self.flow}"
        return self.flow.writes.calldata.value

    @property
    @override
    def child_caller(self) -> HexString:
        return self.call_context.storage_address

    def get_return_writes(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> StorageWrites:
        assert env.last_executed_sub_context, f"Tried to get call return writes, but did not find last executed sub context: {env}"
        child_context = env.last_executed_sub_context
        _, _, _, _, offset_access, size_access = self.flow.accesses.stack
        offset = offset_access.value.get_hexstring().as_int()
        size = size_access.value.get_hexstring().as_int()
        if size == 0:
            mem_writes = []
        else:
            return_data = child_context.return_data
            return_data_slice = return_data[:size]
            mem_writes = [MemoryWrite(offset, return_data_slice)]
        success = "0x0" if child_context.reverted else "0x1"
        stack_push = StackPush(
            StorageByteGroup.from_hexstring(
                HexString(success).as_size(32), self.step_index
            )
        )
        return StorageWrites(stack_pushes=[stack_push], memory=mem_writes)

    def get_immediate_return_writes(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> StorageWrites:
        _, _, _, _, offset_access, size_access = self.flow.accesses.stack
        offset = offset_access.value.get_hexstring().as_int()
        size = size_access.value.get_hexstring().as_int()
        return_data_slice = output_oracle.memory[offset * 2 : (offset + size) * 2]
        success = StorageByteGroup.from_hexstring(
            output_oracle.stack[0], self.step_index
        )
        return StorageWrites(
            stack_pushes=[StackPush(success)],
            memory=[
                MemoryWrite(
                    offset,
                    StorageByteGroup.from_hexstring(return_data_slice, self.step_index),
                )
            ],
        )


@dataclass(frozen=True, repr=False, eq=False)
class DELEGATECALL(CallInstruction):
    flow_spec = combine(
        stack_arg(0),
        stack_arg(1),
        calldata_write(mem_range(stack_arg(2), stack_arg(3))),
        # memory expansion on return (see CALL)
        mem_range(stack_arg(4), stack_arg(5)),
        callvalue(),
    )

    @property
    @override
    def child_code_address(self) -> HexString:
        return self.flow.accesses.stack[1].value.get_hexstring().as_address()

    @property
    @override
    def child_storage_address(self) -> HexString:
        return self.call_context.storage_address

    @property
    @override
    def child_value(self) -> StorageByteGroup:
        return self.flow.accesses.callvalue[0].value

    @property
    @override
    def child_input(self) -> StorageByteGroup:
        assert (
            self.flow.writes.calldata is not None
        ), f"Tried to get DELEGATECALL data but contains no write for it: {self.flow}"
        return self.flow.writes.calldata.value

    @property
    @override
    def child_caller(self) -> HexString:
        return self.call_context.msg_sender

    @override
    def get_return_writes(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> StorageWrites:
        assert env.last_executed_sub_context, f"Tried to get call return writes, but did not find last executed sub context: {env}"
        child_context = env.last_executed_sub_context
        _, _, _, _, offset_access, size_access = self.flow.accesses.stack
        offset = offset_access.value.get_hexstring().as_int()
        size = size_access.value.get_hexstring().as_int()
        if size == 0:
            mem_writes = []
        else:
            return_data = child_context.return_data
            return_data_slice = return_data[:size]
            mem_writes = [MemoryWrite(offset, return_data_slice)]
        success = "0x0" if child_context.reverted else "0x1"
        stack_push = StackPush(
            StorageByteGroup.from_hexstring(
                HexString(success).as_size(32), self.step_index
            )
        )
        return StorageWrites(stack_pushes=[stack_push], memory=mem_writes)

    @override
    def get_immediate_return_writes(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> StorageWrites:
        _, _, _, _, offset_access, size_access = self.flow.accesses.stack
        offset = offset_access.value.get_hexstring().as_int()
        size = size_access.value.get_hexstring().as_int()
        return_data_slice = output_oracle.memory[offset * 2 : (offset + size) * 2]
        success = StorageByteGroup.from_hexstring(
            output_oracle.stack[0], self.step_index
        )
        return StorageWrites(
            stack_pushes=[StackPush(success)],
            memory=[
                MemoryWrite(
                    offset,
                    StorageByteGroup.from_hexstring(return_data_slice, self.step_index),
                )
            ],
        )


@dataclass(frozen=True, repr=False, eq=False)
class CALLCODE(CallInstruction):
    flow_spec = combine(
        stack_arg(0),
        balance_transfer(current_storage_address(), stack_arg(1), stack_arg(2)),
        calldata_write(mem_range(stack_arg(3), stack_arg(4))),
        # memory expansion on return (see CALL)
        mem_range(stack_arg(5), stack_arg(6)),
    )

    @property
    @override
    def child_code_address(self) -> HexString:
        return self.flow.accesses.stack[1].value.get_hexstring().as_address()

    @property
    @override
    def child_storage_address(self) -> HexString:
        return self.call_context.storage_address

    @property
    @override
    def child_value(self) -> StorageByteGroup:
        return self.flow.accesses.stack[2].value

    @property
    @override
    def child_input(self) -> StorageByteGroup:
        assert (
            self.flow.writes.calldata is not None
        ), f"Tried to get CALLCODE data but contains no write for it: {self.flow}"
        return self.flow.writes.calldata.value

    @property
    @override
    def child_caller(self) -> HexString:
        return self.call_context.storage_address

    def get_return_writes(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> StorageWrites:
        assert env.last_executed_sub_context, f"Tried to get call return writes, but did not find last executed sub context: {env}"
        child_context = env.last_executed_sub_context
        _, _, _, _, _, offset_access, size_access = self.flow.accesses.stack
        offset = offset_access.value.get_hexstring().as_int()
        size = size_access.value.get_hexstring().as_int()
        if size == 0:
            mem_writes = []
        else:
            return_data = child_context.return_data
            return_data_slice = return_data[:size]
            mem_writes = [MemoryWrite(offset, return_data_slice)]
        success = "0x0" if child_context.reverted else "0x1"
        stack_push = StackPush(
            StorageByteGroup.from_hexstring(
                HexString(success).as_size(32), self.step_index
            )
        )
        return StorageWrites(stack_pushes=[stack_push], memory=mem_writes)

    @override
    def get_immediate_return_writes(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> StorageWrites:
        _, _, _, _, _, offset_access, size_access = self.flow.accesses.stack
        offset = offset_access.value.get_hexstring().as_int()
        size = size_access.value.get_hexstring().as_int()
        return_data_slice = output_oracle.memory[offset * 2 : (offset + size) * 2]
        success = StorageByteGroup.from_hexstring(
            output_oracle.stack[0], self.step_index
        )
        return StorageWrites(
            stack_pushes=[StackPush(success)],
            memory=[
                MemoryWrite(
                    offset,
                    StorageByteGroup.from_hexstring(return_data_slice, self.step_index),
                )
            ],
        )


def _make_flow(io_flow_spec: FlowSpec | None = None):
    spec = io_flow_spec or noop()

    @dataclass(frozen=True, repr=False, eq=False)
    class FlowInstruction(Instruction):
        flow_spec = spec

    return FlowInstruction


STOP = _make_flow()

ADD = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
MUL = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
SUB = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
DIV = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
SDIV = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))

MOD = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
SMOD = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
ADDMOD = _make_flow(
    combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1), stack_arg(2))
)
MULMOD = _make_flow(
    combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1), stack_arg(2))
)
EXP = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
SIGNEXTEND = _make_flow(
    combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1))
)
LT = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
GT = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
SLT = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
SGT = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
EQ = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
ISZERO = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0)))
AND = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
OR = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
XOR = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
NOT = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0)))
BYTE = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
SHL = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
SHR = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))
SAR = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0), stack_arg(1)))

KECCAK256 = _make_flow(
    combine(stack_push(oracle_stack_peek(0)), mem_range(stack_arg(0), stack_arg(1)))
)
ADDRESS = _make_flow(stack_push(current_storage_address()))
BALANCE = _make_flow(
    combine(stack_push(oracle_stack_peek(0)), balance_of(to_size(stack_arg(0), 20)))
)
ORIGIN = _make_flow(stack_push(oracle_stack_peek(0)))
CALLER = _make_flow(stack_push(oracle_stack_peek(0)))
CALLVALUE = _make_flow(stack_push(callvalue()))
CALLDATALOAD = _make_flow(stack_push(calldata_range(stack_arg(0), 32)))
CALLDATASIZE = _make_flow(stack_push(calldata_size()))
CALLDATACOPY = _make_flow(
    mem_write(stack_arg(0), calldata_range(stack_arg(1), stack_arg(2)))
)

CODESIZE = _make_flow(combine(stack_push(oracle_stack_peek(0))))

CODECOPY = _make_flow(
    combine(
        mem_write(stack_arg(0), oracle_mem_range_peek(stack_peek(0), stack_arg(2))),
        stack_arg(1),
    )
)
EXTCODECOPY = _make_flow(
    combine(
        stack_arg(0),
        stack_arg(2),
        mem_write(stack_arg(1), oracle_mem_range_peek(stack_arg(1), stack_arg(3))),
    )
)


GASPRICE = _make_flow(stack_push(oracle_stack_peek(0)))
EXTCODESIZE = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0)))

RETURNDATASIZE = _make_flow(stack_push(return_data_size()))
RETURNDATACOPY = _make_flow(
    mem_write(stack_arg(0), return_data_range(stack_arg(1), stack_arg(2)))
)


EXTCODEHASH = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0)))
BLOCKHASH = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0)))
COINBASE = _make_flow(stack_push(oracle_stack_peek(0)))
TIMESTAMP = _make_flow(stack_push(oracle_stack_peek(0)))
NUMBER = _make_flow(stack_push(oracle_stack_peek(0)))
PREVRANDAO = _make_flow(stack_push(oracle_stack_peek(0)))
GASLIMIT = _make_flow(stack_push(oracle_stack_peek(0)))
CHAINID = _make_flow(stack_push(oracle_stack_peek(0)))
SELFBALANCE = _make_flow(
    combine(stack_push(oracle_stack_peek(0)), balance_of(current_storage_address()))
)
BASEFEE = _make_flow(stack_push(oracle_stack_peek(0)))
BLOBHASH = _make_flow(combine(stack_push(oracle_stack_peek(0)), stack_arg(0)))
BLOBBASEFEE = _make_flow(stack_push(oracle_stack_peek(0)))

POP = _make_flow(stack_arg(0))

MLOAD = _make_flow(stack_push(mem_range(stack_arg(0), 32)))
MSTORE = _make_flow(mem_write(stack_arg(0), stack_arg(1)))
MSTORE8 = _make_flow(mem_write(stack_arg(0), to_size(stack_arg(1), 1)))

SLOAD = _make_flow(stack_push(persistent_storage_get(stack_arg(0))))
SSTORE = _make_flow(persistent_storage_set(stack_arg(0), stack_arg(1)))
JUMP = _make_flow(stack_arg(0))
JUMPI = _make_flow(combine(stack_arg(0), stack_arg(1)))
PC = _make_flow(stack_push(oracle_stack_peek(0)))
MSIZE = _make_flow(stack_push(mem_size()))
GAS = _make_flow(stack_push(oracle_stack_peek(0)))
JUMPDEST = _make_flow()
TLOAD = _make_flow(stack_push(transient_storage_get(stack_arg(0))))
TSTORE = _make_flow(transient_storage_set(stack_arg(0), stack_arg(1)))

MCOPY = _make_flow(mem_write(stack_arg(0), mem_range(stack_arg(1), stack_arg(2))))

PUSH0 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH1 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH2 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH3 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH4 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH5 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH6 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH7 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH8 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH9 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH10 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH11 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH12 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH13 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH14 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH15 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH16 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH17 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH18 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH19 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH20 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH21 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH22 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH23 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH24 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH25 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH26 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH27 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH28 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH29 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH30 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH31 = _make_flow(stack_push(oracle_stack_peek(0)))
PUSH32 = _make_flow(stack_push(oracle_stack_peek(0)))

DUP1 = _make_flow(combine(stack_push(stack_peek(0))))
DUP2 = _make_flow(combine(stack_push(stack_peek(1))))
DUP3 = _make_flow(combine(stack_push(stack_peek(2))))
DUP4 = _make_flow(combine(stack_push(stack_peek(3))))
DUP5 = _make_flow(combine(stack_push(stack_peek(4))))
DUP6 = _make_flow(combine(stack_push(stack_peek(5))))
DUP7 = _make_flow(combine(stack_push(stack_peek(6))))
DUP8 = _make_flow(combine(stack_push(stack_peek(7))))
DUP9 = _make_flow(combine(stack_push(stack_peek(8))))
DUP10 = _make_flow(combine(stack_push(stack_peek(9))))
DUP11 = _make_flow(combine(stack_push(stack_peek(10))))
DUP12 = _make_flow(combine(stack_push(stack_peek(11))))
DUP13 = _make_flow(combine(stack_push(stack_peek(12))))
DUP14 = _make_flow(combine(stack_push(stack_peek(13))))
DUP15 = _make_flow(combine(stack_push(stack_peek(14))))
DUP16 = _make_flow(combine(stack_push(stack_peek(15))))

SWAP1 = _make_flow(combine(stack_set(0, stack_peek(1)), stack_set(1, stack_peek(0))))
SWAP2 = _make_flow(combine(stack_set(0, stack_peek(2)), stack_set(2, stack_peek(0))))
SWAP3 = _make_flow(combine(stack_set(0, stack_peek(3)), stack_set(3, stack_peek(0))))
SWAP4 = _make_flow(combine(stack_set(0, stack_peek(4)), stack_set(4, stack_peek(0))))
SWAP5 = _make_flow(combine(stack_set(0, stack_peek(5)), stack_set(5, stack_peek(0))))
SWAP6 = _make_flow(combine(stack_set(0, stack_peek(6)), stack_set(6, stack_peek(0))))
SWAP7 = _make_flow(combine(stack_set(0, stack_peek(7)), stack_set(7, stack_peek(0))))
SWAP8 = _make_flow(combine(stack_set(0, stack_peek(8)), stack_set(8, stack_peek(0))))
SWAP9 = _make_flow(combine(stack_set(0, stack_peek(9)), stack_set(9, stack_peek(0))))
SWAP10 = _make_flow(combine(stack_set(0, stack_peek(10)), stack_set(10, stack_peek(0))))
SWAP11 = _make_flow(combine(stack_set(0, stack_peek(11)), stack_set(11, stack_peek(0))))
SWAP12 = _make_flow(combine(stack_set(0, stack_peek(12)), stack_set(12, stack_peek(0))))
SWAP13 = _make_flow(combine(stack_set(0, stack_peek(13)), stack_set(13, stack_peek(0))))
SWAP14 = _make_flow(combine(stack_set(0, stack_peek(14)), stack_set(14, stack_peek(0))))
SWAP15 = _make_flow(combine(stack_set(0, stack_peek(15)), stack_set(15, stack_peek(0))))
SWAP16 = _make_flow(combine(stack_set(0, stack_peek(16)), stack_set(16, stack_peek(0))))

LOG0 = _make_flow(combine(mem_range(stack_arg(0), stack_arg(1))))
LOG1 = _make_flow(combine(mem_range(stack_arg(0), stack_arg(1)), stack_arg(2)))
LOG2 = _make_flow(
    combine(mem_range(stack_arg(0), stack_arg(1)), stack_arg(2), stack_arg(3))
)
LOG3 = _make_flow(
    combine(
        mem_range(stack_arg(0), stack_arg(1)), stack_arg(2), stack_arg(3), stack_arg(4)
    )
)
LOG4 = _make_flow(
    combine(
        mem_range(stack_arg(0), stack_arg(1)),
        stack_arg(2),
        stack_arg(3),
        stack_arg(4),
        stack_arg(5),
    )
)


@dataclass(frozen=True, repr=False, eq=False)
class CREATE(ContractCreatingInstruction):
    # NOTE: we don't use the correct creation address here,
    # but we probably should sync it with how we compute it later on
    flow_spec = combine(
        balance_transfer(current_storage_address(), "abcd1234" * 8, stack_arg(0)),
        mem_range(stack_arg(1), stack_arg(2)),
    )

    def get_return_writes(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> StorageWrites:
        return StorageWrites()

    def _compute_child_address(self) -> HexString:
        # we do not care about correctness of this value
        # we only want determinism if the same CREATE is called in another run
        return HexString(
            "0x"
            + sha256(self.call_context.code_address.with_prefix().encode()).hexdigest()[
                12:
            ]
        )

    @property
    @override
    def child_code_address(self) -> HexString:
        return self._compute_child_address()

    @property
    @override
    def child_storage_address(self) -> HexString:
        return self._compute_child_address()

    @property
    @override
    def child_value(self) -> StorageByteGroup:
        # TODO: no value?
        return StorageByteGroup.from_hexstring(HexString.zeros(32), self.step_index)

    @property
    @override
    def child_input(self) -> StorageByteGroup:
        # TODO: has CREATE no calldata? Is initialization code no calldata?
        return StorageByteGroup()

    @property
    @override
    def child_caller(self) -> HexString:
        return self.call_context.storage_address


@dataclass(frozen=True, repr=False, eq=False)
class CREATE2(ContractCreatingInstruction):
    flow_spec = combine(
        balance_transfer(current_storage_address(), "abcd1234" * 8, stack_arg(0)),
        mem_range(stack_arg(1), stack_arg(2)),
        stack_arg(3),
    )

    def get_return_writes(
        self, env: ParsingEnvironment, output_oracle: InstructionOutputOracle
    ) -> StorageWrites:
        return StorageWrites()

    def _compute_child_address(self) -> HexString:
        # we do not care about correctness of this value
        # we only want determinism if the same CREATE is called in another run
        return HexString(
            "0x"
            + sha256(self.call_context.code_address.with_prefix().encode()).hexdigest()[
                12:
            ]
        )

    @property
    @override
    def child_code_address(self) -> HexString:
        return self._compute_child_address()

    @property
    @override
    def child_storage_address(self) -> HexString:
        return self._compute_child_address()

    @property
    @override
    def child_value(self) -> StorageByteGroup:
        # TODO: no value?
        return StorageByteGroup.from_hexstring(HexString.zeros(32), self.step_index)

    @property
    @override
    def child_input(self) -> StorageByteGroup:
        # TODO: has CREATE2 no calldata? Is initialization code no calldata?
        return StorageByteGroup()

    @property
    @override
    def child_caller(self) -> HexString:
        return self.call_context.storage_address


RETURN = _make_flow(return_data_write(mem_range(stack_arg(0), stack_arg(1))))
REVERT = _make_flow(return_data_write(mem_range(stack_arg(0), stack_arg(1))))

INVALID = _make_flow()
SELFDESTRUCT = _make_flow(selfdestruct(current_storage_address(), stack_arg(0)))

_INSTRUCTIONS: Mapping[int, type[Instruction]] = {
    0x00: STOP,
    0x01: ADD,
    0x02: MUL,
    0x03: SUB,
    0x04: DIV,
    0x05: SDIV,
    0x06: MOD,
    0x07: SMOD,
    0x08: ADDMOD,
    0x09: MULMOD,
    0x0A: EXP,
    0x0B: SIGNEXTEND,
    0x10: LT,
    0x11: GT,
    0x12: SLT,
    0x13: SGT,
    0x14: EQ,
    0x15: ISZERO,
    0x16: AND,
    0x17: OR,
    0x18: XOR,
    0x19: NOT,
    0x1A: BYTE,
    0x1B: SHL,
    0x1C: SHR,
    0x1D: SAR,
    0x20: KECCAK256,
    0x30: ADDRESS,
    0x31: BALANCE,
    0x32: ORIGIN,
    0x33: CALLER,
    0x34: CALLVALUE,
    0x35: CALLDATALOAD,
    0x36: CALLDATASIZE,
    0x37: CALLDATACOPY,
    0x38: CODESIZE,
    0x39: CODECOPY,
    0x3A: GASPRICE,
    0x3B: EXTCODESIZE,
    0x3C: EXTCODECOPY,
    0x3D: RETURNDATASIZE,
    0x3E: RETURNDATACOPY,
    0x3F: EXTCODEHASH,
    0x40: BLOCKHASH,
    0x41: COINBASE,
    0x42: TIMESTAMP,
    0x43: NUMBER,
    0x44: PREVRANDAO,
    0x45: GASLIMIT,
    0x46: CHAINID,
    0x47: SELFBALANCE,
    0x48: BASEFEE,
    0x49: BLOBHASH,
    0x4A: BLOBBASEFEE,
    0x50: POP,
    0x51: MLOAD,
    0x52: MSTORE,
    0x53: MSTORE8,
    0x54: SLOAD,
    0x55: SSTORE,
    0x56: JUMP,
    0x57: JUMPI,
    0x58: PC,
    0x59: MSIZE,
    0x5A: GAS,
    0x5B: JUMPDEST,
    0x5C: TLOAD,
    0x5D: TSTORE,
    0x5E: MCOPY,
    0x5F: PUSH0,
    0x60: PUSH1,
    0x61: PUSH2,
    0x62: PUSH3,
    0x63: PUSH4,
    0x64: PUSH5,
    0x65: PUSH6,
    0x66: PUSH7,
    0x67: PUSH8,
    0x68: PUSH9,
    0x69: PUSH10,
    0x6A: PUSH11,
    0x6B: PUSH12,
    0x6C: PUSH13,
    0x6D: PUSH14,
    0x6E: PUSH15,
    0x6F: PUSH16,
    0x70: PUSH17,
    0x71: PUSH18,
    0x72: PUSH19,
    0x73: PUSH20,
    0x74: PUSH21,
    0x75: PUSH22,
    0x76: PUSH23,
    0x77: PUSH24,
    0x78: PUSH25,
    0x79: PUSH26,
    0x7A: PUSH27,
    0x7B: PUSH28,
    0x7C: PUSH29,
    0x7D: PUSH30,
    0x7E: PUSH31,
    0x7F: PUSH32,
    0x80: DUP1,
    0x81: DUP2,
    0x82: DUP3,
    0x83: DUP4,
    0x84: DUP5,
    0x85: DUP6,
    0x86: DUP7,
    0x87: DUP8,
    0x88: DUP9,
    0x89: DUP10,
    0x8A: DUP11,
    0x8B: DUP12,
    0x8C: DUP13,
    0x8D: DUP14,
    0x8E: DUP15,
    0x8F: DUP16,
    0x90: SWAP1,
    0x91: SWAP2,
    0x92: SWAP3,
    0x93: SWAP4,
    0x94: SWAP5,
    0x95: SWAP6,
    0x96: SWAP7,
    0x97: SWAP8,
    0x98: SWAP9,
    0x99: SWAP10,
    0x9A: SWAP11,
    0x9B: SWAP12,
    0x9C: SWAP13,
    0x9D: SWAP14,
    0x9E: SWAP15,
    0x9F: SWAP16,
    0xA0: LOG0,
    0xA1: LOG1,
    0xA2: LOG2,
    0xA3: LOG3,
    0xA4: LOG4,
    0xF0: CREATE,
    0xF1: CALL,
    0xF2: CALLCODE,
    0xF3: RETURN,
    0xF4: DELEGATECALL,
    0xF5: CREATE2,
    0xFA: STATICCALL,
    0xFD: REVERT,
    0xFE: INVALID,
    0xFF: SELFDESTRUCT,
}

# set the opcodes so we can access eg CALL.opcode
for opcode, instruction_class in _INSTRUCTIONS.items():
    instruction_class.opcode = opcode


def get_instruction_class(opcode: int) -> type[Instruction] | None:
    return _INSTRUCTIONS.get(opcode)
