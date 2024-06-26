from typing import TypeVar, cast

from tests.test_utils.test_utils import (
    _test_addr,
    _test_call_context,
    _test_group,
    _test_group32,
    _test_hash_addr,
    _test_oracle,
    _test_root,
    mock_env,
)
from traces_parser.parser.environment.parsing_environment import (
    InstructionOutputOracle,
    ParsingEnvironment,
)
from traces_parser.parser.information_flow.constant_step_indexes import (
    SPECIAL_STEP_INDEXES,
)
from traces_parser.parser.instructions.instruction import Instruction
from traces_parser.parser.instructions.instructions import (
    ADD,
    ADDMOD,
    ADDRESS,
    AND,
    BALANCE,
    BASEFEE,
    BLOBBASEFEE,
    BLOBHASH,
    BLOCKHASH,
    BYTE,
    CALL,
    CALLCODE,
    CALLDATACOPY,
    CALLDATALOAD,
    CALLDATASIZE,
    CALLER,
    CALLVALUE,
    CHAINID,
    CODECOPY,
    CODESIZE,
    COINBASE,
    CREATE,
    CREATE2,
    DELEGATECALL,
    DIV,
    DUP1,
    DUP10,
    DUP11,
    DUP12,
    DUP13,
    DUP14,
    DUP15,
    DUP16,
    DUP2,
    DUP3,
    DUP4,
    DUP5,
    DUP6,
    DUP7,
    DUP8,
    DUP9,
    EQ,
    EXP,
    EXTCODECOPY,
    EXTCODEHASH,
    EXTCODESIZE,
    GAS,
    GASLIMIT,
    GASPRICE,
    GT,
    INVALID,
    ISZERO,
    JUMP,
    JUMPDEST,
    JUMPI,
    KECCAK256,
    LOG0,
    LOG1,
    LOG2,
    LOG3,
    LOG4,
    LT,
    MCOPY,
    MLOAD,
    MOD,
    MSIZE,
    MSTORE,
    MSTORE8,
    MUL,
    MULMOD,
    NOT,
    NUMBER,
    OR,
    ORIGIN,
    PC,
    POP,
    PREVRANDAO,
    PUSH0,
    PUSH1,
    PUSH10,
    PUSH11,
    PUSH12,
    PUSH13,
    PUSH14,
    PUSH15,
    PUSH16,
    PUSH17,
    PUSH18,
    PUSH19,
    PUSH2,
    PUSH20,
    PUSH21,
    PUSH22,
    PUSH23,
    PUSH24,
    PUSH25,
    PUSH26,
    PUSH27,
    PUSH28,
    PUSH29,
    PUSH3,
    PUSH30,
    PUSH31,
    PUSH32,
    PUSH4,
    PUSH5,
    PUSH6,
    PUSH7,
    PUSH8,
    PUSH9,
    RETURN,
    RETURNDATACOPY,
    RETURNDATASIZE,
    REVERT,
    SAR,
    SDIV,
    SELFBALANCE,
    SELFDESTRUCT,
    SGT,
    SHL,
    SHR,
    SIGNEXTEND,
    SLOAD,
    SLT,
    SMOD,
    SSTORE,
    STATICCALL,
    STOP,
    SUB,
    SWAP1,
    SWAP10,
    SWAP11,
    SWAP12,
    SWAP13,
    SWAP14,
    SWAP15,
    SWAP16,
    SWAP2,
    SWAP3,
    SWAP4,
    SWAP5,
    SWAP6,
    SWAP7,
    SWAP8,
    SWAP9,
    TIMESTAMP,
    TLOAD,
    TSTORE,
    XOR,
    get_instruction_class,
)
from traces_parser.parser.instructions_parser import InstructionMetadata
from traces_parser.parser.trace_evm.trace_evm import parse_instruction
from traces_parser.datatypes.hexstring import HexString


_opcodes_to_instruction = [
    (0x00, STOP),
    (0x01, ADD),
    (0x02, MUL),
    (0x03, SUB),
    (0x04, DIV),
    (0x05, SDIV),
    (0x06, MOD),
    (0x07, SMOD),
    (0x08, ADDMOD),
    (0x09, MULMOD),
    (0x0A, EXP),
    (0x0B, SIGNEXTEND),
    (0x10, LT),
    (0x11, GT),
    (0x12, SLT),
    (0x13, SGT),
    (0x14, EQ),
    (0x15, ISZERO),
    (0x16, AND),
    (0x17, OR),
    (0x18, XOR),
    (0x19, NOT),
    (0x1A, BYTE),
    (0x1B, SHL),
    (0x1C, SHR),
    (0x1D, SAR),
    (0x20, KECCAK256),
    (0x30, ADDRESS),
    (0x31, BALANCE),
    (0x32, ORIGIN),
    (0x33, CALLER),
    (0x34, CALLVALUE),
    (0x35, CALLDATALOAD),
    (0x36, CALLDATASIZE),
    (0x37, CALLDATACOPY),
    (0x38, CODESIZE),
    (0x39, CODECOPY),
    (0x3A, GASPRICE),
    (0x3B, EXTCODESIZE),
    (0x3C, EXTCODECOPY),
    (0x3D, RETURNDATASIZE),
    (0x3E, RETURNDATACOPY),
    (0x3F, EXTCODEHASH),
    (0x40, BLOCKHASH),
    (0x41, COINBASE),
    (0x42, TIMESTAMP),
    (0x43, NUMBER),
    (0x44, PREVRANDAO),
    (0x45, GASLIMIT),
    (0x46, CHAINID),
    (0x47, SELFBALANCE),
    (0x48, BASEFEE),
    (0x49, BLOBHASH),
    (0x4A, BLOBBASEFEE),
    (0x50, POP),
    (0x51, MLOAD),
    (0x52, MSTORE),
    (0x53, MSTORE8),
    (0x54, SLOAD),
    (0x55, SSTORE),
    (0x56, JUMP),
    (0x57, JUMPI),
    (0x58, PC),
    (0x59, MSIZE),
    (0x5A, GAS),
    (0x5B, JUMPDEST),
    (0x5C, TLOAD),
    (0x5D, TSTORE),
    (0x5E, MCOPY),
    (0x5F, PUSH0),
    (0x60, PUSH1),
    (0x61, PUSH2),
    (0x62, PUSH3),
    (0x63, PUSH4),
    (0x64, PUSH5),
    (0x65, PUSH6),
    (0x66, PUSH7),
    (0x67, PUSH8),
    (0x68, PUSH9),
    (0x69, PUSH10),
    (0x6A, PUSH11),
    (0x6B, PUSH12),
    (0x6C, PUSH13),
    (0x6D, PUSH14),
    (0x6E, PUSH15),
    (0x6F, PUSH16),
    (0x70, PUSH17),
    (0x71, PUSH18),
    (0x72, PUSH19),
    (0x73, PUSH20),
    (0x74, PUSH21),
    (0x75, PUSH22),
    (0x76, PUSH23),
    (0x77, PUSH24),
    (0x78, PUSH25),
    (0x79, PUSH26),
    (0x7A, PUSH27),
    (0x7B, PUSH28),
    (0x7C, PUSH29),
    (0x7D, PUSH30),
    (0x7E, PUSH31),
    (0x7F, PUSH32),
    (0x80, DUP1),
    (0x81, DUP2),
    (0x82, DUP3),
    (0x83, DUP4),
    (0x84, DUP5),
    (0x85, DUP6),
    (0x86, DUP7),
    (0x87, DUP8),
    (0x88, DUP9),
    (0x89, DUP10),
    (0x8A, DUP11),
    (0x8B, DUP12),
    (0x8C, DUP13),
    (0x8D, DUP14),
    (0x8E, DUP15),
    (0x8F, DUP16),
    (0x90, SWAP1),
    (0x91, SWAP2),
    (0x92, SWAP3),
    (0x93, SWAP4),
    (0x94, SWAP5),
    (0x95, SWAP6),
    (0x96, SWAP7),
    (0x97, SWAP8),
    (0x98, SWAP9),
    (0x99, SWAP10),
    (0x9A, SWAP11),
    (0x9B, SWAP12),
    (0x9C, SWAP13),
    (0x9D, SWAP14),
    (0x9E, SWAP15),
    (0x9F, SWAP16),
    (0xA0, LOG0),
    (0xA1, LOG1),
    (0xA2, LOG2),
    (0xA3, LOG3),
    (0xA4, LOG4),
    (0xF0, CREATE),
    (0xF1, CALL),
    (0xF2, CALLCODE),
    (0xF3, RETURN),
    (0xF4, DELEGATECALL),
    (0xF5, CREATE2),
    (0xFA, STATICCALL),
    (0xFD, REVERT),
    (0xFE, INVALID),
    (0xFF, SELFDESTRUCT),
]


def test_instruction_opcode_matches_class():
    # not using parametrized test for performance
    for opcode, cls in _opcodes_to_instruction:
        assert get_instruction_class(opcode) == cls
        assert cls.opcode == opcode


InstructionType = TypeVar("InstructionType", bound=Instruction)


def _test_parse_instruction(
    instr: type[InstructionType],
    env: ParsingEnvironment,
    output_oracle: InstructionOutputOracle,
) -> InstructionType:
    return cast(
        InstructionType,
        parse_instruction(env, InstructionMetadata(instr.opcode, 0), output_oracle),
    )


simple_stack_instructions = [
    (ADD, 2, 1),
    (MUL, 2, 1),
    (SUB, 2, 1),
    (DIV, 2, 1),
    (SDIV, 2, 1),
    (MOD, 2, 1),
    (SMOD, 2, 1),
    (ADDMOD, 3, 1),
    (MULMOD, 3, 1),
    (EXP, 2, 1),
    (SIGNEXTEND, 2, 1),
    (LT, 2, 1),
    (GT, 2, 1),
    (SLT, 2, 1),
    (SGT, 2, 1),
    (EQ, 2, 1),
    (ISZERO, 1, 1),
    (AND, 2, 1),
    (OR, 2, 1),
    (XOR, 2, 1),
    (NOT, 1, 1),
    (BYTE, 2, 1),
    (SHL, 2, 1),
    (SHR, 2, 1),
    (SAR, 2, 1),
    (PUSH0, 0, 1),
    (PUSH1, 0, 1),
    (PUSH2, 0, 1),
    (PUSH3, 0, 1),
    (PUSH4, 0, 1),
    (PUSH5, 0, 1),
    (PUSH6, 0, 1),
    (PUSH7, 0, 1),
    (PUSH8, 0, 1),
    (PUSH9, 0, 1),
    (PUSH10, 0, 1),
    (PUSH11, 0, 1),
    (PUSH12, 0, 1),
    (PUSH13, 0, 1),
    (PUSH14, 0, 1),
    (PUSH15, 0, 1),
    (PUSH16, 0, 1),
    (POP, 1, 0),
    (CODESIZE, 0, 1),
    (EXTCODESIZE, 1, 1),
    (GASPRICE, 0, 1),
    (EXTCODEHASH, 1, 1),
    (BLOCKHASH, 1, 1),
    (COINBASE, 0, 1),
    (TIMESTAMP, 0, 1),
    (NUMBER, 0, 1),
    (PREVRANDAO, 0, 1),
    (GASLIMIT, 0, 1),
    (CHAINID, 0, 1),
    (BASEFEE, 0, 1),
    (BLOBHASH, 1, 1),
    (BLOBBASEFEE, 0, 1),
    (JUMP, 1, 0),
    (JUMPI, 2, 0),
    (PC, 0, 1),
    (GAS, 0, 1),
    (JUMPDEST, 0, 0),
]


def test_simple_stack_instructions() -> None:
    for instr_type, stack_inputs_n, stack_outputs_n in simple_stack_instructions:
        env = mock_env(
            step_index=3,
            stack_contents=[str(i) for i in range(stack_inputs_n)],
        )
        oracle = _test_oracle(stack=[str(i) for i in range(stack_outputs_n)])

        instr = _test_parse_instruction(instr_type, env, oracle)

        accesses = instr.get_accesses()
        writes = instr.get_writes()
        assert len(accesses.stack) == stack_inputs_n
        assert len(writes.stack_pops) == stack_inputs_n
        for i in range(stack_inputs_n):
            assert accesses.stack[i].index == i
            assert accesses.stack[i].value.get_hexstring() == HexString(str(i)).as_size(
                32
            )

        assert len(writes.stack_pushes) == stack_outputs_n
        for i in range(stack_outputs_n):
            assert writes.stack_pushes[i].value.get_hexstring() == HexString(
                str(i)
            ).as_size(32)
            assert writes.stack_pushes[i].value.depends_on_instruction_indexes() == {3}


DUP_N = [
    DUP1,
    DUP2,
    DUP3,
    DUP4,
    DUP5,
    DUP6,
    DUP7,
    DUP8,
    DUP9,
    DUP10,
    DUP11,
    DUP12,
    DUP13,
    DUP14,
    DUP15,
    DUP16,
]


def test_dupn() -> None:
    for n, dup_type in enumerate(DUP_N):
        env = mock_env(
            step_index=3,
            stack_contents=[
                _test_group(HexString(str(i)).as_size(32), i) for i in range(n + 1)
            ],
        )

        dupn = _test_parse_instruction(dup_type, env, _test_oracle())

        accesses = dupn.get_accesses()
        writes = dupn.get_writes()
        assert len(accesses.stack) == 1
        assert accesses.stack[0].index == n

        assert len(writes.stack_pushes) == 1
        assert writes.stack_pushes[0].value.get_hexstring() == HexString(
            str(n)
        ).as_size(32)
        assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {n}


SWAP_N = [
    SWAP1,
    SWAP2,
    SWAP3,
    SWAP4,
    SWAP5,
    SWAP6,
    SWAP7,
    SWAP8,
    SWAP9,
    SWAP10,
    SWAP11,
    SWAP12,
    SWAP13,
    SWAP14,
    SWAP15,
    SWAP16,
]


def test_swapn() -> None:
    for n, swap_type in enumerate(SWAP_N):
        n += 1
        env = mock_env(
            step_index=3,
            stack_contents=[
                _test_group(HexString(str(i)).as_size(32), i) for i in range(n + 1)
            ],
        )

        swapn = _test_parse_instruction(swap_type, env, _test_oracle())

        accesses = swapn.get_accesses()
        writes = swapn.get_writes()
        assert len(accesses.stack) == 2
        assert accesses.stack[0].index == n
        assert accesses.stack[1].index == 0

        assert len(writes.stack_sets) == 2
        assert writes.stack_sets[0].index == 0
        assert writes.stack_sets[0].value.get_hexstring() == HexString(str(n)).as_size(
            32
        )
        assert writes.stack_sets[0].value.depends_on_instruction_indexes() == {n}
        assert writes.stack_sets[1].index == n
        assert writes.stack_sets[1].value.get_hexstring() == HexString(str(0)).as_size(
            32
        )
        assert writes.stack_sets[1].value.depends_on_instruction_indexes() == {0}


LOG_N = [LOG0, LOG1, LOG2, LOG3, LOG4]


def test_logn() -> None:
    for n, log_type in enumerate(LOG_N):
        env = mock_env(
            step_index=3,
            stack_contents=(
                [_test_group32("2"), _test_group32("4")]
                + [_test_group32(HexString(str(i)).as_size(32), i) for i in range(n)]
            ),  # type: ignore
            memory_content="001122334455667788",
        )

        log = _test_parse_instruction(log_type, env, _test_oracle())

        accesses = log.get_accesses()
        assert len(accesses.stack) == 2 + n
        assert accesses.stack[0].index == 0
        assert accesses.stack[0].value.get_hexstring() == HexString("2").as_size(32)
        assert accesses.stack[1].index == 1
        assert accesses.stack[1].value.get_hexstring() == HexString("4").as_size(32)
        for i in range(n):
            assert accesses.stack[2 + i].index == 2 + i
            assert accesses.stack[2 + i].value.get_hexstring() == HexString(
                str(i)
            ).as_size(32)


def test_keccak256() -> None:
    env = mock_env(
        step_index=3,
        stack_contents=[_test_group32("2", 1), _test_group32("4", 2)],
        memory_content="001122334455667788",
    )
    oracle = _test_oracle(stack=[HexString("aaaa").as_size(32)])

    keccak256 = _test_parse_instruction(KECCAK256, env, oracle)

    accesses = keccak256.get_accesses()
    writes = keccak256.get_writes()
    assert len(writes.stack_pops) == 2
    assert len(accesses.stack) == 2
    assert accesses.stack[0].index == 0
    assert accesses.stack[0].value.get_hexstring() == HexString("2").as_size(32)
    assert accesses.stack[0].value.depends_on_instruction_indexes() == {1}
    assert accesses.stack[1].index == 1
    assert accesses.stack[1].value.get_hexstring() == HexString("4").as_size(32)
    assert accesses.stack[1].value.depends_on_instruction_indexes() == {2}

    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring() == HexString("aaaa").as_size(32)
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {3}


def test_mload() -> None:
    env = mock_env(
        step_index=3,
        storage_step_index=2,
        stack_contents=["2"],
        memory_content="000011223344",
    )

    # load memory[2:34]
    mload = _test_parse_instruction(MLOAD, env, _test_oracle())

    padded_value = "11223344" + (28) * 2 * "0"
    accesses = mload.get_accesses()
    assert len(accesses.memory) == 1
    assert accesses.memory[0].offset == 0x2
    assert accesses.memory[0].value.get_hexstring() == padded_value
    # the access outside of memory range is padded by the current instruction (3)
    assert accesses.memory[0].value.depends_on_instruction_indexes() == {2, 3}


def test_mstore() -> None:
    env = mock_env(stack_contents=["4", _test_group32("11223344", 1)])

    mstore = _test_parse_instruction(MSTORE, env, _test_oracle())

    writes = mstore.get_writes()
    assert len(writes.memory) == 1
    assert writes.memory[0].offset == 0x4
    assert writes.memory[0].value.get_hexstring() == "00" * 28 + "11223344"
    assert writes.memory[0].value.depends_on_instruction_indexes() == {1}


def test_mstore8() -> None:
    env = mock_env(stack_contents=["4", _test_group32("1", 1)])

    mstore8 = _test_parse_instruction(MSTORE8, env, _test_oracle())

    writes = mstore8.get_writes()
    assert len(writes.memory) == 1
    assert writes.memory[0].offset == 0x4
    assert writes.memory[0].value.get_hexstring() == "01"
    assert writes.memory[0].value.depends_on_instruction_indexes() == {1}


def test_msize() -> None:
    content = (
        _test_group32("aa", 0) + _test_group("bb" * 28, 1) + _test_group("cc" * 4, 2)
    )
    env = mock_env(memory_content=content, step_index=1234)

    msize = _test_parse_instruction(MSIZE, env, _test_oracle())

    accesses = msize.get_accesses()
    assert len(accesses.memory) == 1
    # it depends on the last 32 bytes, which are essential for the memory size
    assert accesses.memory[0].offset == 32
    assert accesses.memory[0].value.get_hexstring() == "bb" * 28 + "cc" * 4
    assert accesses.memory[0].value.depends_on_instruction_indexes() == {1, 2}

    writes = msize.get_writes()
    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring().as_int() == 64
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {1234}


def test_mcopy() -> None:
    env = mock_env(
        step_index=2,
        stack_contents=["20", "3", "4"],
        memory_content=_test_group("0000000011223344", 1),
    )

    mcopy = _test_parse_instruction(MCOPY, env, _test_oracle())

    accesses = mcopy.get_accesses()
    assert len(accesses.memory) == 1
    assert accesses.memory[0].offset == 0x3
    assert accesses.memory[0].value.get_hexstring() == "00112233"
    assert accesses.memory[0].value.depends_on_instruction_indexes() == {1}

    writes = mcopy.get_writes()
    assert len(writes.memory) == 1
    assert writes.memory[0].offset == 0x20
    assert writes.memory[0].value.get_hexstring() == "00112233"
    assert writes.memory[0].value.depends_on_instruction_indexes() == {1}


def test_sload_known() -> None:
    call_context = _test_root()
    address = call_context.storage_address
    key = _test_group32("1234", 2)
    value = _test_group32("00112233", 1)
    env = mock_env(
        step_index=3,
        stack_contents=[key],
        persistent_storage={address: {key.get_hexstring(): value}},
    )

    sload = _test_parse_instruction(SLOAD, env, _test_oracle())

    accesses = sload.get_accesses()
    assert len(accesses.stack) == 1
    assert len(accesses.persistent_storage) == 1
    assert accesses.persistent_storage[0].address == address
    assert accesses.persistent_storage[0].key.get_hexstring() == key.get_hexstring()
    assert accesses.persistent_storage[0].key.depends_on_instruction_indexes() == {2}
    assert accesses.persistent_storage[0].value.get_hexstring() == value.get_hexstring()
    assert accesses.persistent_storage[0].value.depends_on_instruction_indexes() == {1}

    writes = sload.get_writes()
    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring() == value.get_hexstring()
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {1}


def test_sload_unknown() -> None:
    call_context = _test_root()
    address = call_context.storage_address
    key = _test_group32("1234", 2)
    value = HexString("00112233").as_size(32)
    env = mock_env(step_index=3, stack_contents=[key], persistent_storage={})
    oracle = _test_oracle(stack=[value])

    sload = _test_parse_instruction(SLOAD, env, oracle)

    accesses = sload.get_accesses()
    assert len(accesses.stack) == 1
    assert len(accesses.persistent_storage) == 1
    assert accesses.persistent_storage[0].address == address
    assert accesses.persistent_storage[0].key.get_hexstring() == key.get_hexstring()
    assert accesses.persistent_storage[0].key.depends_on_instruction_indexes() == {2}
    assert accesses.persistent_storage[0].value.get_hexstring() == value
    # the value has not been set in this transaction, thus SPECIAL_STEP_INDEXES.PRESTATE
    assert accesses.persistent_storage[0].value.depends_on_instruction_indexes() == {
        SPECIAL_STEP_INDEXES.PRESTATE
    }

    writes = sload.get_writes()
    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring() == value
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {3}


def test_sstore() -> None:
    call_context = _test_root()
    address = call_context.storage_address
    key = _test_group32("1234", 2)
    value = _test_group32("00112233", 1)
    env = mock_env(step_index=3, stack_contents=[key, value], persistent_storage={})

    sstore = _test_parse_instruction(SSTORE, env, _test_oracle())

    acesses = sstore.get_accesses()
    assert len(acesses.stack) == 2

    writes = sstore.get_writes()
    assert len(writes.persistent_storage) == 1
    assert writes.persistent_storage[0].address == address
    assert writes.persistent_storage[0].key.get_hexstring() == key.get_hexstring()
    assert writes.persistent_storage[0].key.depends_on_instruction_indexes() == {2}
    assert writes.persistent_storage[0].value.get_hexstring() == value.get_hexstring()
    assert writes.persistent_storage[0].value.depends_on_instruction_indexes() == {1}


def test_tload() -> None:
    call_context = _test_root()
    address = call_context.storage_address
    key = _test_group32("1234", 2)
    value = _test_group32("00112233", 1)
    env = mock_env(
        step_index=3,
        stack_contents=[key],
        transient_storage={address: {key.get_hexstring(): value}},
    )

    tload = _test_parse_instruction(TLOAD, env, _test_oracle())

    accesses = tload.get_accesses()
    assert len(accesses.stack) == 1
    assert len(accesses.transient_storage) == 1
    assert accesses.transient_storage[0].address == address
    assert accesses.transient_storage[0].key.get_hexstring() == key.get_hexstring()
    assert accesses.transient_storage[0].key.depends_on_instruction_indexes() == {2}
    assert accesses.transient_storage[0].value.get_hexstring() == value.get_hexstring()
    assert accesses.transient_storage[0].value.depends_on_instruction_indexes() == {1}

    writes = tload.get_writes()
    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring() == value.get_hexstring()
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {1}


def test_tstore() -> None:
    call_context = _test_root()
    address = call_context.storage_address
    key = _test_group32("1234", 2)
    value = _test_group32("00112233", 1)
    env = mock_env(step_index=3, stack_contents=[key, value], transient_storage={})

    tstore = _test_parse_instruction(TSTORE, env, _test_oracle())

    acesses = tstore.get_accesses()
    assert len(acesses.stack) == 2

    writes = tstore.get_writes()
    assert len(writes.transient_storage) == 1
    assert writes.transient_storage[0].address == address
    assert writes.transient_storage[0].key.get_hexstring() == key.get_hexstring()
    assert writes.transient_storage[0].key.depends_on_instruction_indexes() == {2}
    assert writes.transient_storage[0].value.get_hexstring() == value.get_hexstring()
    assert writes.transient_storage[0].value.depends_on_instruction_indexes() == {1}


def test_address() -> None:
    call_context = _test_root()
    env = mock_env(
        current_call_context=call_context,
        step_index=2,
    )

    address = _test_parse_instruction(ADDRESS, env, _test_oracle())

    writes = address.get_writes()
    assert len(writes.stack_pushes) == 1
    assert (
        writes.stack_pushes[0].value.get_hexstring().as_address()
        == call_context.storage_address
    )
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {2}


def test_balance() -> None:
    env = mock_env(
        storage_step_index=1,
        step_index=2,
        stack_contents=["abcd"],
        balances={"abcd": 12},
    )
    oracle = _test_oracle(stack=["123456"])

    balance = _test_parse_instruction(BALANCE, env, oracle)

    accesses = balance.get_accesses()
    assert len(accesses.balance) == 1
    assert accesses.balance[0].address.get_hexstring() == _test_addr("abcd")
    assert accesses.balance[0].address.depends_on_instruction_indexes() == {1}
    assert accesses.balance[0].last_modified_step_index == 12

    assert len(accesses.stack) == 1
    assert accesses.stack[0].index == 0
    assert accesses.stack[0].value.get_hexstring() == HexString("abcd").as_size(32)
    assert accesses.stack[0].value.depends_on_instruction_indexes() == {1}

    writes = balance.get_writes()
    assert len(writes.stack_pops) == 1
    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring().as_int() == 0x123456
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {2}


def test_selfbalance() -> None:
    call_context = _test_root()
    storage_addr = call_context.storage_address
    env = mock_env(
        step_index=2,
        storage_step_index=1,
        balances={storage_addr: 12},
    )
    oracle = _test_oracle(stack=["123456"])

    balance = _test_parse_instruction(SELFBALANCE, env, oracle)

    accesses = balance.get_accesses()
    assert len(accesses.balance) == 1
    assert accesses.balance[0].address.get_hexstring() == storage_addr
    assert accesses.balance[0].address.depends_on_instruction_indexes() == {2}
    assert accesses.balance[0].last_modified_step_index == 12

    writes = balance.get_writes()
    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring().as_int() == 0x123456
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {2}


def test_origin() -> None:
    env = mock_env(
        step_index=2,
    )
    oracle = _test_oracle(stack=[_test_hash_addr("origin")])

    origin = _test_parse_instruction(ORIGIN, env, oracle)

    writes = origin.get_writes()
    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring().as_address() == _test_hash_addr(
        "origin"
    )
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {2}


def test_caller() -> None:
    env = mock_env(
        step_index=2,
    )
    oracle = _test_oracle(stack=[_test_hash_addr("sender")])

    caller = _test_parse_instruction(CALLER, env, oracle)

    writes = caller.get_writes()
    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring().as_address() == _test_hash_addr(
        "sender"
    )
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {2}


def test_callvalue() -> None:
    call_context = _test_call_context(value=_test_group32("1234", 1))
    env = mock_env(
        current_call_context=call_context,
    )

    callvalue = _test_parse_instruction(CALLVALUE, env, _test_oracle())

    accesses = callvalue.get_accesses()
    assert len(accesses.callvalue) == 1
    assert accesses.callvalue[0].value.get_hexstring().as_int() == 0x1234
    assert accesses.callvalue[0].value.depends_on_instruction_indexes() == {1}

    writes = callvalue.get_writes()
    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring().as_int() == 0x1234
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {1}


def test_calldataload() -> None:
    call_context = _test_call_context(calldata=_test_group("0011223344556677", 1))
    env = mock_env(
        current_call_context=call_context,
        storage_step_index=2,
        step_index=3,
        stack_contents=["4"],
    )

    calldataload = _test_parse_instruction(CALLDATALOAD, env, _test_oracle())

    accesses = calldataload.get_accesses()
    assert len(accesses.stack) == 1
    assert accesses.stack[0].index == 0
    assert accesses.stack[0].value.get_hexstring() == HexString("4").as_size(32)
    assert accesses.stack[0].value.depends_on_instruction_indexes() == {2}
    assert len(accesses.calldata) == 1
    assert accesses.calldata[0].offset == 4
    assert accesses.calldata[0].value.get_hexstring() == "44556677" + "00" * 28
    assert accesses.calldata[0].value.depends_on_instruction_indexes() == {1, 3}

    writes = calldataload.get_writes()
    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring() == "44556677" + "00" * 28
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {1, 3}


def test_calldatasize() -> None:
    call_context = _test_call_context(calldata=_test_group("0011223344556677", 1))
    env = mock_env(
        current_call_context=call_context,
        step_index=2,
    )

    calldatasize = _test_parse_instruction(CALLDATASIZE, env, _test_oracle())

    accesses = calldatasize.get_accesses()
    assert len(accesses.calldata) == 1
    assert accesses.calldata[0].offset == 0
    assert accesses.calldata[0].value.get_hexstring() == "0011223344556677"
    assert accesses.calldata[0].value.depends_on_instruction_indexes() == {1}

    writes = calldatasize.get_writes()
    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring() == HexString("8").as_size(32)
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {2}


def test_calldatacopy() -> None:
    call_context = _test_call_context(calldata=_test_group("0011223344556677", 1))
    env = mock_env(
        current_call_context=call_context,
        storage_step_index=2,
        step_index=3,
        stack_contents=["8", "4", hex(16)],
    )

    calldatacopy = _test_parse_instruction(CALLDATACOPY, env, _test_oracle())

    accesses = calldatacopy.get_accesses()
    assert len(accesses.stack) == 3
    assert len(accesses.calldata) == 1
    assert accesses.calldata[0].offset == 4
    assert accesses.calldata[0].value.get_hexstring() == "44556677" + "00" * 12
    assert accesses.calldata[0].value.depends_on_instruction_indexes() == {1, 3}

    writes = calldatacopy.get_writes()
    assert len(writes.memory) == 1
    assert writes.memory[0].offset == 8
    assert writes.memory[0].value.get_hexstring() == "44556677" + "00" * 12
    assert writes.memory[0].value.depends_on_instruction_indexes() == {1, 3}


def test_codecopy() -> None:
    env = mock_env(
        step_index=1234,
        stack_contents=["4", "1234", hex(16)],
    )
    oracle = _test_oracle(memory="0011223344556677")

    codecopy = _test_parse_instruction(CODECOPY, env, oracle)

    accesses = codecopy.get_accesses()
    assert len(accesses.stack) == 3

    writes = codecopy.get_writes()
    assert len(writes.memory) == 1
    assert writes.memory[0].offset == 4
    assert writes.memory[0].value.get_hexstring() == "44556677" + "00" * 12
    assert writes.memory[0].value.depends_on_instruction_indexes() == {1234}


def test_extcodecopy() -> None:
    env = mock_env(
        step_index=1234,
        stack_contents=["abcdef", "4", "1234", hex(16)],
    )
    oracle = _test_oracle(memory="0011223344556677")

    extcodecopy = _test_parse_instruction(EXTCODECOPY, env, oracle)

    accesses = extcodecopy.get_accesses()
    assert len(accesses.stack) == 4

    writes = extcodecopy.get_writes()
    assert len(writes.memory) == 1
    assert writes.memory[0].offset == 4
    assert writes.memory[0].value.get_hexstring() == "44556677" + "00" * 12
    assert writes.memory[0].value.depends_on_instruction_indexes() == {1234}


def test_return() -> None:
    env = mock_env(
        stack_contents=["2", "4"],
        memory_content=_test_group("1122334455667788", 1),
    )

    return_instr = _test_parse_instruction(RETURN, env, _test_oracle())

    accesses = return_instr.get_accesses()
    assert len(accesses.memory) == 1
    assert accesses.memory[0].offset == 2
    assert accesses.memory[0].value.get_hexstring() == "33445566"
    assert accesses.memory[0].value.depends_on_instruction_indexes() == {1}

    writes = return_instr.get_writes()
    assert writes.return_data
    assert writes.return_data.value.get_hexstring() == "33445566"
    assert writes.return_data.value.depends_on_instruction_indexes() == {1}


def test_revert() -> None:
    env = mock_env(
        stack_contents=["2", "4"],
        memory_content=_test_group("1122334455667788", 1),
    )

    revert = _test_parse_instruction(REVERT, env, _test_oracle())

    accesses = revert.get_accesses()
    assert len(accesses.memory) == 1
    assert accesses.memory[0].value.get_hexstring() == "33445566"
    assert accesses.memory[0].value.depends_on_instruction_indexes() == {1}

    writes = revert.get_writes()
    assert writes.return_data
    assert writes.return_data.value.get_hexstring() == "33445566"
    assert writes.return_data.value.depends_on_instruction_indexes() == {1}


def test_returndatasize() -> None:
    env = mock_env(step_index=2)
    env.last_executed_sub_context.return_data = _test_group("112233445566", 1)

    returndatasize = _test_parse_instruction(RETURNDATASIZE, env, _test_oracle())

    accesses = returndatasize.get_accesses()
    assert accesses.return_data
    assert accesses.return_data.offset == 0
    assert accesses.return_data.size == 6
    assert accesses.return_data.value.get_hexstring() == "112233445566"
    assert accesses.return_data.value.depends_on_instruction_indexes() == {1}

    writes = returndatasize.get_writes()
    assert len(writes.stack_pushes) == 1
    assert writes.stack_pushes[0].value.get_hexstring().as_int() == 6
    assert writes.stack_pushes[0].value.depends_on_instruction_indexes() == {2}


def test_returndatacopy() -> None:
    env = mock_env(
        stack_contents=["123", "2", "4"],
    )
    env.last_executed_sub_context.return_data = _test_group("1122334455667788", 1234)

    returndatasize = _test_parse_instruction(RETURNDATACOPY, env, _test_oracle())

    accesses = returndatasize.get_accesses()
    assert accesses.return_data
    assert accesses.return_data.offset == 2
    assert accesses.return_data.size == 4
    assert accesses.return_data.value.get_hexstring() == "33445566"
    assert accesses.return_data.value.depends_on_instruction_indexes() == {1234}

    writes = returndatasize.get_writes()
    assert len(writes.memory) == 1
    assert writes.memory[0].offset == 0x123
    assert writes.memory[0].value.get_hexstring() == "33445566"
    assert writes.memory[0].value.depends_on_instruction_indexes() == {1234}


def test_call_enter() -> None:
    call_context = _test_root()
    env = mock_env(
        storage_step_index=1,
        step_index=2,
        stack_contents=[
            "1234",
            _test_hash_addr("call target"),
            "10",
            "2",
            "4",
            "20",
            "8",
        ],
        memory_content="1122334455667788",
        balances={call_context.storage_address: 1},
        current_call_context=call_context,
    )

    call = _test_parse_instruction(CALL, env, _test_oracle())

    accesses = call.get_accesses()
    assert len(accesses.stack) == 7
    assert len(accesses.memory) == 2
    assert accesses.memory[0].offset == 0x2
    assert accesses.memory[0].value.get_hexstring() == "33445566"
    assert accesses.memory[0].value.depends_on_instruction_indexes() == {1}
    assert len(accesses.balance) == 1
    assert accesses.balance[0].address.get_hexstring() == call_context.storage_address
    assert accesses.balance[0].last_modified_step_index == 1

    writes = call.get_writes()
    assert writes.calldata
    assert writes.calldata.value.get_hexstring() == "33445566"
    assert writes.calldata.value.depends_on_instruction_indexes() == {1}
    assert len(writes.balance_transfers) == 1
    assert (
        writes.balance_transfers[0].address_from.get_hexstring()
        == call_context.storage_address
    )
    assert writes.balance_transfers[
        0
    ].address_from.depends_on_instruction_indexes() == {2}
    assert writes.balance_transfers[0].address_to.get_hexstring() == _test_hash_addr(
        "call target"
    )
    assert writes.balance_transfers[0].address_to.depends_on_instruction_indexes() == {
        1
    }
    assert writes.balance_transfers[0].value.get_hexstring().as_int() == 0x10
    assert writes.balance_transfers[0].value.depends_on_instruction_indexes() == {1}

    assert call.child_code_address == _test_hash_addr("call target")
    assert call.child_storage_address == _test_hash_addr("call target")


def test_staticcall_enter() -> None:
    env = mock_env(
        storage_step_index=1,
        stack_contents=[
            "1234",
            _test_hash_addr("call target"),
            "2",
            "4",
            "20",
            "8",
        ],
        memory_content="1122334455667788",
    )

    staticcall = _test_parse_instruction(STATICCALL, env, _test_oracle())

    accesses = staticcall.get_accesses()
    assert len(accesses.stack) == 6
    assert len(accesses.memory) == 2
    assert accesses.memory[0].offset == 0x2
    assert accesses.memory[0].value.get_hexstring() == "33445566"
    assert accesses.memory[0].value.depends_on_instruction_indexes() == {1}

    writes = staticcall.get_writes()
    assert writes.calldata
    assert writes.calldata.value.get_hexstring() == "33445566"
    assert writes.calldata.value.depends_on_instruction_indexes() == {1}

    assert staticcall.child_code_address == _test_hash_addr("call target")
    assert staticcall.child_storage_address == _test_hash_addr("call target")


def test_callcode_enter() -> None:
    call_context = _test_root()
    env = mock_env(
        storage_step_index=1,
        step_index=2,
        stack_contents=[
            "1234",
            _test_hash_addr("call target"),
            "10",
            "2",
            "4",
            "20",
            "8",
        ],
        memory_content="1122334455667788",
        balances={call_context.storage_address: 1},
        current_call_context=call_context,
    )

    callcode = _test_parse_instruction(CALLCODE, env, _test_oracle())

    accesses = callcode.get_accesses()
    assert len(accesses.stack) == 7
    assert len(accesses.memory) == 2
    assert accesses.memory[0].offset == 0x2
    assert accesses.memory[0].value.get_hexstring() == "33445566"
    assert accesses.memory[0].value.depends_on_instruction_indexes() == {1}
    assert len(accesses.balance) == 1
    assert accesses.balance[0].address.get_hexstring() == call_context.storage_address
    assert accesses.balance[0].last_modified_step_index == 1

    writes = callcode.get_writes()
    assert writes.calldata
    assert writes.calldata.value.get_hexstring() == "33445566"
    assert writes.calldata.value.depends_on_instruction_indexes() == {1}
    assert (
        writes.balance_transfers[0].address_from.get_hexstring()
        == call_context.storage_address
    )
    assert writes.balance_transfers[
        0
    ].address_from.depends_on_instruction_indexes() == {2}
    assert writes.balance_transfers[0].address_to.get_hexstring() == _test_hash_addr(
        "call target"
    )
    assert writes.balance_transfers[0].address_to.depends_on_instruction_indexes() == {
        1
    }
    assert writes.balance_transfers[0].value.get_hexstring().as_int() == 0x10
    assert writes.balance_transfers[0].value.depends_on_instruction_indexes() == {1}

    assert callcode.child_code_address == _test_hash_addr("call target")
    assert callcode.child_storage_address == call_context.storage_address


def test_delegatecall_enter() -> None:
    call_context = _test_root()
    env = mock_env(
        current_call_context=call_context,
        storage_step_index=1,
        stack_contents=[
            "1234",
            _test_hash_addr("call target"),
            "2",
            "4",
            "20",
            "8",
        ],
        memory_content="1122334455667788",
    )

    delegatecall = _test_parse_instruction(DELEGATECALL, env, _test_oracle())

    accesses = delegatecall.get_accesses()
    assert len(accesses.stack) == 6
    assert len(accesses.memory) == 2
    assert accesses.memory[0].offset == 0x2
    assert accesses.memory[0].value.get_hexstring() == "33445566"
    assert accesses.memory[0].value.depends_on_instruction_indexes() == {1}

    writes = delegatecall.get_writes()
    assert writes.calldata
    assert writes.calldata.value.get_hexstring() == "33445566"
    assert writes.calldata.value.depends_on_instruction_indexes() == {1}

    assert delegatecall.child_code_address == _test_hash_addr("call target")
    assert delegatecall.child_storage_address == call_context.storage_address


def test_create() -> None:
    call_context = _test_root()
    env = mock_env(
        storage_step_index=1,
        step_index=2,
        stack_contents=[
            "1000",
            "2",
            "4",
        ],
        memory_content="1122334455667788",
        balances={call_context.storage_address: 1},
        current_call_context=call_context,
    )

    create = _test_parse_instruction(CREATE, env, _test_oracle())

    accesses = create.get_accesses()
    assert len(accesses.stack) == 3
    assert len(accesses.memory) == 1
    assert accesses.memory[0].offset == 0x2
    assert accesses.memory[0].value.get_hexstring() == "33445566"
    assert accesses.memory[0].value.depends_on_instruction_indexes() == {1}
    assert len(accesses.balance) == 1
    assert accesses.balance[0].address.get_hexstring() == call_context.storage_address
    assert accesses.balance[0].last_modified_step_index == 1

    writes = create.get_writes()
    assert (
        writes.balance_transfers[0].address_from.get_hexstring()
        == call_context.storage_address
    )
    assert writes.balance_transfers[
        0
    ].address_from.depends_on_instruction_indexes() == {2}
    # NOTE: we don't compute the created address properly, so we don't test it here
    assert writes.balance_transfers[0].address_to.depends_on_instruction_indexes() == {
        2
    }
    assert writes.balance_transfers[0].value.get_hexstring().as_int() == 0x1000
    assert writes.balance_transfers[0].value.depends_on_instruction_indexes() == {1}


def test_create2() -> None:
    call_context = _test_root()
    env = mock_env(
        storage_step_index=1,
        step_index=2,
        stack_contents=["1000", "2", "4", "5a1d5a1d5a1d"],
        memory_content="1122334455667788",
        balances={call_context.storage_address: 1},
        current_call_context=call_context,
    )

    create2 = _test_parse_instruction(CREATE2, env, _test_oracle())

    accesses = create2.get_accesses()
    assert len(accesses.stack) == 4
    assert len(accesses.memory) == 1
    assert accesses.memory[0].offset == 0x2
    assert accesses.memory[0].value.get_hexstring() == "33445566"
    assert accesses.memory[0].value.depends_on_instruction_indexes() == {1}
    assert len(accesses.balance) == 1
    assert accesses.balance[0].address.get_hexstring() == call_context.storage_address
    assert accesses.balance[0].last_modified_step_index == 1

    writes = create2.get_writes()
    assert (
        writes.balance_transfers[0].address_from.get_hexstring()
        == call_context.storage_address
    )
    assert writes.balance_transfers[
        0
    ].address_from.depends_on_instruction_indexes() == {2}
    # NOTE: we don't compute the created address properly, so we don't test it here
    assert writes.balance_transfers[0].address_to.depends_on_instruction_indexes() == {
        2
    }
    assert writes.balance_transfers[0].value.get_hexstring().as_int() == 0x1000
    assert writes.balance_transfers[0].value.depends_on_instruction_indexes() == {1}


def test_selfdestruct() -> None:
    call_context = _test_root()
    env = mock_env(
        storage_step_index=1,
        step_index=2,
        stack_contents=[
            _test_hash_addr("recipient"),
        ],
        balances={call_context.storage_address: 1},
        current_call_context=call_context,
    )

    selfdestruct = _test_parse_instruction(SELFDESTRUCT, env, _test_oracle())

    accesses = selfdestruct.get_accesses()
    assert len(accesses.stack) == 1
    assert len(accesses.balance) == 1
    assert accesses.balance[0].address.get_hexstring() == call_context.storage_address
    assert accesses.balance[0].last_modified_step_index == 1

    writes = selfdestruct.get_writes()
    assert len(writes.selfdestruct) == 1
    assert (
        writes.selfdestruct[0].address_from.get_hexstring()
        == call_context.storage_address
    )
    assert writes.selfdestruct[0].address_from.depends_on_instruction_indexes() == {2}
    assert writes.selfdestruct[0].address_to.get_hexstring() == _test_hash_addr(
        "recipient"
    )
    assert writes.selfdestruct[0].address_to.depends_on_instruction_indexes() == {1}
