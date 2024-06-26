from tests.test_utils.test_utils import (
    _test_addr,
    _test_call_context,
    _test_child,
    _test_group,
    _test_group32,
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
from traces_parser.parser.information_flow.information_flow_dsl import (
    balance_of,
    balance_transfer,
    calldata_size,
    callvalue,
    combine,
    mem_size,
    oracle_mem_range_peek,
    persistent_storage_get,
    selfdestruct,
    calldata_range,
    calldata_write,
    current_storage_address,
    mem_range,
    mem_write,
    noop,
    oracle_stack_peek,
    return_data_range,
    return_data_size,
    return_data_write,
    stack_arg,
    stack_peek,
    stack_push,
    stack_set,
    to_size,
    transient_storage_get,
    transient_storage_set,
)
from traces_parser.parser.information_flow.information_flow_dsl_implementation import (
    FlowNodeWithResult,
    FlowWithResult,
)
from traces_parser.datatypes.storage_byte_group import StorageByteGroup
from traces_parser.parser.storage.storage_writes import (
    ReturnDataAccess,
    StorageAccesses,
    StorageWrites,
)
from traces_parser.datatypes.hexstring import HexString


class _TestFlowNode(FlowNodeWithResult):
    def __init__(self, value: StorageByteGroup) -> None:
        super().__init__(())
        self.value = value

    def _get_result(
        self,
        args: tuple[FlowWithResult, ...],
        env: ParsingEnvironment,
        output_oracle: InstructionOutputOracle,
    ) -> FlowWithResult:
        return FlowWithResult(
            accesses=StorageAccesses(),
            writes=StorageWrites(),
            result=self.value,
        )


def _test_node(
    value: StorageByteGroup | HexString | str,
    step_index=SPECIAL_STEP_INDEXES.TEST_DEFAULT,
) -> FlowNodeWithResult:
    return _TestFlowNode(value=_test_group(value, step_index))


def test_noop():
    env = mock_env()

    flow = noop().compute(env, _test_oracle())

    assert flow.accesses == StorageAccesses()
    assert flow.writes == StorageWrites()


def test_combine():
    env = mock_env(stack_contents=["1", "2"])

    flow = combine(stack_arg(0), stack_arg(1)).compute(env, _test_oracle())

    assert len(flow.accesses.stack) == 2
    assert flow.accesses.stack[0].index == 0
    assert flow.accesses.stack[1].index == 1


def test_stack_arg():
    env = mock_env(stack_contents=[_test_group32("10", 1234)])

    flow = stack_arg(0).compute(env, _test_oracle())

    assert len(flow.accesses.stack) == 1
    assert flow.accesses.stack[0].index == 0
    assert flow.accesses.stack[0].value.get_hexstring() == "10".rjust(64, "0")
    assert flow.accesses.stack[0].value.depends_on_instruction_indexes() == {1234}

    assert len(flow.writes.stack_pops) == 1

    assert flow.result == flow.accesses.stack[0].value


def test_stack_peek():
    env = mock_env(stack_contents=[_test_group32("10", 1234)])

    flow = stack_peek(0).compute(env, _test_oracle())

    assert len(flow.accesses.stack) == 1
    assert flow.accesses.stack[0].index == 0
    assert flow.accesses.stack[0].value.get_hexstring() == "10".rjust(64, "0")
    assert flow.accesses.stack[0].value.depends_on_instruction_indexes() == {1234}

    assert len(flow.writes.stack_pops) == 0

    assert flow.result == flow.accesses.stack[0].value


def test_oracle_stack_peek():
    env = mock_env(step_index=1234)
    oracle = _test_oracle(stack=["10", "20"])

    flow = oracle_stack_peek(1).compute(env, oracle)

    assert flow.result.get_hexstring() == HexString("20").as_size(32)
    assert flow.result.depends_on_instruction_indexes() == {1234}


def test_oracle_mem_range_peek():
    env = mock_env(step_index=1234)
    oracle = _test_oracle(memory="0011223344556677")

    flow = oracle_mem_range_peek(2, 4).compute(env, oracle)

    assert flow.result.get_hexstring() == "22334455"
    assert flow.result.depends_on_instruction_indexes() == {1234}


def test_mem_range_const():
    env = mock_env(memory_content=_test_group("00112233445566778899", 1234))

    flow = mem_range(2, 4).compute(env, _test_oracle())

    assert flow.result.get_hexstring() == "22334455"
    assert len(flow.accesses.memory) == 1
    assert flow.accesses.memory[0].offset == 2
    assert flow.accesses.memory[0].value == _test_group("22334455")
    assert flow.accesses.memory[0].value.depends_on_instruction_indexes() == {1234}


def test_mem_range_stack_args():
    env = mock_env(
        stack_contents=["2", "4"],
        memory_content=_test_group("00112233445566778899", 1234),
    )

    flow = mem_range(stack_arg(0), stack_arg(1)).compute(env, _test_oracle())

    assert flow.result.get_hexstring() == "22334455"
    assert flow.result.depends_on_instruction_indexes() == {1234}


def test_mem_size():
    content = (
        _test_group32("aa", 0) + _test_group("bb" * 28, 1) + _test_group("cc" * 4, 2)
    )
    env = mock_env(memory_content=content, step_index=1234)

    flow = mem_size().compute(env, _test_oracle())

    assert len(flow.accesses.memory) == 1
    # it depends on the last 32 bytes, which are essential for the memory size
    assert flow.accesses.memory[0].offset == 32
    assert flow.accesses.memory[0].value.get_hexstring() == "bb" * 28 + "cc" * 4
    assert flow.accesses.memory[0].value.depends_on_instruction_indexes() == {1, 2}

    assert flow.result.get_hexstring().as_int() == 64
    assert flow.result.depends_on_instruction_indexes() == {1234}


def test_persistent_storage_known():
    call_context = _test_child()
    address = call_context.storage_address
    key = HexString("1234").as_size(32)
    env = mock_env(
        current_call_context=call_context,
        persistent_storage={address: {key: _test_group32("00112233", 1)}},
    )

    flow = persistent_storage_get(_test_node(key, 2)).compute(env, _test_oracle())

    assert len(flow.accesses.persistent_storage) == 1
    assert flow.accesses.persistent_storage[0].address == address
    assert flow.accesses.persistent_storage[0].key.get_hexstring() == key
    assert flow.accesses.persistent_storage[0].key.depends_on_instruction_indexes() == {
        2
    }
    assert flow.accesses.persistent_storage[0].value.get_hexstring() == HexString(
        "00112233"
    ).as_size(32)
    assert flow.accesses.persistent_storage[
        0
    ].value.depends_on_instruction_indexes() == {1}

    assert flow.result.get_hexstring() == HexString("00112233").as_size(32)
    assert flow.result.depends_on_instruction_indexes() == {1}


def test_persistent_storage_unknown():
    call_context = _test_child()
    address = call_context.storage_address
    value = HexString("00112233").as_size(32)
    key = HexString("1234").as_size(32)
    env = mock_env(
        current_call_context=call_context,
        step_index=1,
        persistent_storage={address: {}},
    )
    oracle = _test_oracle(stack=[value])

    flow = persistent_storage_get(_test_node(key, 2)).compute(env, oracle)

    assert len(flow.accesses.persistent_storage) == 1
    assert flow.accesses.persistent_storage[0].address == address
    assert flow.accesses.persistent_storage[0].key.get_hexstring() == key
    assert flow.accesses.persistent_storage[0].key.depends_on_instruction_indexes() == {
        2
    }
    assert flow.accesses.persistent_storage[0].value.get_hexstring() == value
    assert flow.accesses.persistent_storage[
        0
    ].value.depends_on_instruction_indexes() == {SPECIAL_STEP_INDEXES.PRESTATE}

    assert flow.result.get_hexstring() == HexString("00112233").as_size(32)
    assert flow.result.depends_on_instruction_indexes() == {1}


def test_transient_storage_get():
    call_context = _test_child()
    address = call_context.storage_address
    key = HexString("1234").as_size(32)
    env = mock_env(
        current_call_context=call_context,
        transient_storage={address: {key: _test_group32("00112233", 1)}},
    )

    flow = transient_storage_get(_test_node(key, 2)).compute(env, _test_oracle())

    assert len(flow.accesses.transient_storage) == 1
    assert flow.accesses.transient_storage[0].address == address
    assert flow.accesses.transient_storage[0].key.get_hexstring() == key
    assert flow.accesses.transient_storage[0].key.depends_on_instruction_indexes() == {
        2
    }
    assert flow.accesses.transient_storage[0].value.get_hexstring() == HexString(
        "00112233"
    ).as_size(32)
    assert flow.accesses.transient_storage[
        0
    ].value.depends_on_instruction_indexes() == {1}

    assert flow.result.get_hexstring() == HexString("00112233").as_size(32)
    assert flow.result.depends_on_instruction_indexes() == {1}


def test_transient_storage_get_unknown():
    call_context = _test_child()
    address = call_context.storage_address
    key = HexString("1234").as_size(32)
    env = mock_env(
        step_index=3,
        current_call_context=call_context,
        transient_storage={},
    )

    flow = transient_storage_get(_test_node(key, 2)).compute(env, _test_oracle())

    assert len(flow.accesses.transient_storage) == 1
    assert flow.accesses.transient_storage[0].address == address
    assert flow.accesses.transient_storage[0].key.get_hexstring() == key
    assert flow.accesses.transient_storage[0].key.depends_on_instruction_indexes() == {
        2
    }
    assert flow.accesses.transient_storage[0].value.get_hexstring() == HexString.zeros(
        32
    )
    assert flow.accesses.transient_storage[
        0
    ].value.depends_on_instruction_indexes() == {3}

    assert flow.result.get_hexstring() == HexString.zeros(32)
    assert flow.result.depends_on_instruction_indexes() == {3}


def test_transient_storage_set():
    call_context = _test_child()
    address = call_context.storage_address
    key = HexString("1234").as_size(32)
    value = HexString("00112233").as_size(32)
    env = mock_env(
        current_call_context=call_context,
        transient_storage={},
    )

    flow = transient_storage_set(_test_node(key, 2), _test_node(value, 1)).compute(
        env, _test_oracle()
    )

    assert len(flow.writes.transient_storage) == 1
    assert flow.writes.transient_storage[0].address == address
    assert flow.writes.transient_storage[0].key.get_hexstring() == key
    assert flow.writes.transient_storage[0].key.depends_on_instruction_indexes() == {2}
    assert flow.writes.transient_storage[0].value.get_hexstring() == value
    assert flow.writes.transient_storage[0].value.depends_on_instruction_indexes() == {
        1
    }


def test_stack_push_const():
    env = mock_env(step_index=1234)

    flow = stack_push("123456").compute(env, _test_oracle())

    assert len(flow.writes.stack_pushes) == 1
    assert flow.writes.stack_pushes[0].value.get_hexstring() == HexString(
        "123456"
    ).as_size(32)
    assert flow.writes.stack_pushes[0].value.depends_on_instruction_indexes() == {1234}


def test_stack_push_node():
    env = mock_env(step_index=5678)
    input = _test_node(_test_group("123456", 1234))

    flow = stack_push(input).compute(env, _test_oracle())

    assert len(flow.writes.stack_pushes) == 1
    assert flow.writes.stack_pushes[0].value.get_hexstring() == HexString(
        "123456"
    ).as_size(32)
    assert flow.writes.stack_pushes[0].value.depends_on_instruction_indexes() == {
        1234,
        5678,
    }


def test_stack_set_const():
    env = mock_env(step_index=1234)

    flow = stack_set(3, "123456").compute(env, _test_oracle())

    assert len(flow.writes.stack_sets) == 1
    assert flow.writes.stack_sets[0].index == 3
    assert flow.writes.stack_sets[0].value.get_hexstring() == "123456"
    assert flow.writes.stack_sets[0].value.depends_on_instruction_indexes() == {1234}


def test_stack_set_node():
    env = mock_env()
    input = _test_node(_test_group("123456", 1234))

    flow = stack_set(_test_node("3"), input).compute(env, _test_oracle())

    assert len(flow.writes.stack_sets) == 1
    assert flow.writes.stack_sets[0].index == 3
    assert flow.writes.stack_sets[0].value.get_hexstring() == "123456"
    assert flow.writes.stack_sets[0].value.depends_on_instruction_indexes() == {1234}


def test_mem_write_const():
    env = mock_env(step_index=1234)

    flow = mem_write(2, "22334455").compute(env, _test_oracle())

    assert not flow.accesses.memory
    assert len(flow.writes.memory) == 1
    assert flow.writes.memory[0].offset == 2
    assert flow.writes.memory[0].value.get_hexstring() == "22334455"
    assert flow.writes.memory[0].value.depends_on_instruction_indexes() == {1234}


def test_current_address():
    call_context = _test_root()
    env = mock_env(step_index=1234, current_call_context=call_context)

    flow = current_storage_address().compute(env, _test_oracle())

    assert flow.result.get_hexstring() == call_context.storage_address
    assert flow.result.depends_on_instruction_indexes() == {1234}
    assert len(flow.result) == 20


def test_balance_of_known_address():
    env = mock_env(balances={"abcd": 1234})

    flow = balance_of(_test_node(HexString("abcd").as_address(), 2)).compute(
        env, _test_oracle()
    )

    assert len(flow.accesses.balance) == 1
    assert (
        flow.accesses.balance[0].address.get_hexstring()
        == HexString("abcd").as_address()
    )
    assert flow.accesses.balance[0].address.depends_on_instruction_indexes() == {2}
    assert flow.accesses.balance[0].last_modified_step_index == 1234


def test_balance_of_unknown_address():
    env = mock_env(balances={})

    flow = balance_of(_test_node(HexString("abcd").as_address(), 2)).compute(
        env, _test_oracle()
    )

    assert len(flow.accesses.balance) == 1
    assert (
        flow.accesses.balance[0].address.get_hexstring()
        == HexString("abcd").as_address()
    )
    assert flow.accesses.balance[0].address.depends_on_instruction_indexes() == {2}
    assert (
        flow.accesses.balance[0].last_modified_step_index
        == SPECIAL_STEP_INDEXES.PRESTATE
    )


def test_balance_transfer():
    env = mock_env(balances={"abcd": 4}, step_index=1234)
    from_node = _test_node(_test_addr("abcd"), 1)
    to_node = _test_node(_test_addr("cdef"), 2)
    value_node = _test_node("1000", 3)

    flow = balance_transfer(from_node, to_node, value_node).compute(env, _test_oracle())

    assert len(flow.accesses.balance) == 1
    assert (
        flow.accesses.balance[0].address.get_hexstring()
        == HexString("abcd").as_address()
    )
    assert flow.accesses.balance[0].address.depends_on_instruction_indexes() == {1}
    assert flow.accesses.balance[0].last_modified_step_index == 4

    assert len(flow.writes.balance_transfers) == 1
    assert flow.writes.balance_transfers[0].address_from.get_hexstring() == _test_addr(
        "abcd"
    )
    assert flow.writes.balance_transfers[0].address_to.get_hexstring() == _test_addr(
        "cdef"
    )
    assert flow.writes.balance_transfers[0].value.get_hexstring().as_int() == 0x1000


def test_selfdestruct():
    env = mock_env(balances={"abcd": 4}, step_index=1234)
    from_node = _test_node(_test_addr("abcd"), 1)
    to_node = _test_node(_test_addr("cdef"), 2)

    flow = selfdestruct(from_node, to_node).compute(env, _test_oracle())

    assert len(flow.accesses.balance) == 1
    assert (
        flow.accesses.balance[0].address.get_hexstring()
        == HexString("abcd").as_address()
    )
    assert flow.accesses.balance[0].address.depends_on_instruction_indexes() == {1}
    assert flow.accesses.balance[0].last_modified_step_index == 4

    assert len(flow.writes.selfdestruct) == 1
    assert flow.writes.selfdestruct[0].address_from.get_hexstring() == _test_addr(
        "abcd"
    )
    assert flow.writes.selfdestruct[0].address_to.get_hexstring() == _test_addr("cdef")

    assert (
        env.balances.last_modified_at_step_index(HexString("cdef").as_address()) == 1234
    )


def test_to_size_noop():
    env = mock_env()
    input = _test_node(_test_group("11223344", 1234))

    flow = to_size(input, 4).compute(env, _test_oracle())

    assert len(flow.result) == 4
    assert flow.result.depends_on_instruction_indexes() == {1234}


def test_to_size_increase():
    env = mock_env(step_index=2)
    input = _test_node(_test_group("1122", 1))

    flow = to_size(input, 4).compute(env, _test_oracle())

    assert len(flow.result) == 4
    assert flow.result.depends_on_instruction_indexes() == {1, 2}


def test_to_size_decrease():
    env = mock_env(step_index=2)
    input = _test_node(_test_group("112233445566", 1))

    flow = to_size(input, 4).compute(env, _test_oracle())

    assert len(flow.result) == 4
    assert flow.result.depends_on_instruction_indexes() == {1}


def test_return_data_range_noop():
    env = mock_env()
    env.last_executed_sub_context.return_data = _test_group("1234", 1)

    flow = return_data_range(_test_node("2"), _test_node("0")).compute(
        env, _test_oracle()
    )

    assert len(flow.result) == 0
    assert flow.accesses.return_data is None


def test_return_data_range_if_not_set():
    env = mock_env()
    env.last_executed_sub_context.return_data = _test_group("", 1234)

    flow = return_data_range(_test_node("2"), _test_node("4")).compute(
        env, _test_oracle()
    )

    assert len(flow.result) == 0
    assert flow.accesses.return_data
    assert flow.accesses.return_data.offset == 2
    assert flow.accesses.return_data.size == 4
    assert flow.accesses.return_data.value.get_hexstring() == ""
    assert len(flow.accesses.return_data.value.depends_on_instruction_indexes()) == 0


def test_return_data_range():
    env = mock_env()
    env.last_executed_sub_context.return_data = _test_group(
        "11223344556677889900", 1234
    )

    flow = return_data_range(_test_node("2"), _test_node("4")).compute(
        env, _test_oracle()
    )

    assert len(flow.result) == 4
    assert flow.result == _test_group("33445566")
    assert flow.accesses.return_data
    assert flow.accesses.return_data == ReturnDataAccess(2, 4, _test_group("33445566"))
    assert flow.accesses.return_data.value.depends_on_instruction_indexes() == {1234}


def test_calldata_range():
    call_context = _test_call_context(calldata=_test_group("0011223344556677", 1))
    env = mock_env(step_index=3, current_call_context=call_context)

    flow = calldata_range(_test_node("4", 2), 32).compute(env, _test_oracle())

    assert len(flow.accesses.calldata) == 1
    assert flow.accesses.calldata[0].offset == 4
    assert flow.accesses.calldata[0].value.get_hexstring() == "44556677" + "00" * 28
    assert flow.accesses.calldata[0].value.depends_on_instruction_indexes() == {1, 3}


def test_calldata_size():
    call_context = _test_call_context(calldata=_test_group("0011223344556677", 1))
    env = mock_env(step_index=2, current_call_context=call_context)

    flow = calldata_size().compute(env, _test_oracle())

    assert len(flow.accesses.calldata) == 1
    assert flow.accesses.calldata[0].offset == 0
    assert flow.accesses.calldata[0].value.get_hexstring() == "0011223344556677"
    assert flow.accesses.calldata[0].value.depends_on_instruction_indexes() == {1}

    assert flow.result.get_hexstring().as_int() == 8
    assert flow.result.depends_on_instruction_indexes() == {2}


def test_calldata_write():
    env = mock_env()
    input = _test_node(_test_group("11223344", 1234))

    flow = calldata_write(input).compute(env, _test_oracle())

    assert flow.writes.calldata
    assert flow.writes.calldata.value.get_hexstring() == "11223344"
    assert flow.writes.calldata.value.depends_on_instruction_indexes() == {1234}


def test_callvalue():
    call_context = _test_call_context(value=_test_group("1234", 1))
    env = mock_env(current_call_context=call_context)

    flow = callvalue().compute(env, _test_oracle())

    assert len(flow.accesses.callvalue) == 1
    assert flow.accesses.callvalue[0].value.get_hexstring().as_int() == 0x1234
    assert flow.accesses.callvalue[0].value.depends_on_instruction_indexes() == {1}

    assert flow.result.get_hexstring().as_int() == 0x1234
    assert flow.result.depends_on_instruction_indexes() == {1}


def test_return_data_write():
    env = mock_env()
    input = _test_node(_test_group("11223344", 1234))

    flow = return_data_write(input).compute(env, _test_oracle())

    assert flow.writes.return_data
    assert flow.writes.return_data.value.get_hexstring() == "11223344"
    assert flow.writes.return_data.value.depends_on_instruction_indexes() == {1234}


def test_return_data_size():
    env = mock_env(step_index=1)
    env.last_executed_sub_context.return_data = _test_group("11" * 40, 1234)

    flow = return_data_size().compute(env, _test_oracle())

    assert flow.accesses.return_data
    assert flow.accesses.return_data.offset == 0
    assert flow.accesses.return_data.size == 40
    assert flow.accesses.return_data.value.get_hexstring() == HexString("11" * 40)
    assert flow.accesses.return_data.value.depends_on_instruction_indexes() == {1234}

    assert flow.result.get_hexstring().as_int() == 40
