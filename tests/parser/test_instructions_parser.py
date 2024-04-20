from traces_analyzer.parser.call_context import CallContext
from traces_analyzer.parser.call_context_manager import CallContextManager
from traces_analyzer.parser.events_parser import TraceEvent
from traces_analyzer.parser.instructions import (
    CALL,
    POP,
)
from traces_analyzer.parser.instructions_parser import _parse_instructions


def get_root_call_context():
    return CallContext(
        parent=None,
        calldata="",
        depth=1,
        msg_sender="0x1111111111111111111111111111111111111111",
        code_address="0x1234123412341234123412341234123412341234",
        storage_address="0x1234123412341234123412341234123412341234",
    )


def get_sample_call_context_manager():
    return CallContextManager(get_root_call_context())


def test_parser_empty_events():
    assert list(_parse_instructions([], get_sample_call_context_manager())) == []


def test_call_inputs_memory_parsing():
    call_context_manager = get_sample_call_context_manager()
    stack = ["0x0", "0x4bb", "0x24", "0xb", "0x0", "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "0x940f"]
    memory = "00000000000000000000002e1a7d4d000000000000000000000000000000000000000000000000016345785d8a000000000000000000000000000000000000000000"

    call_event = TraceEvent(pc=1234, op=CALL.opcode, stack=stack, memory=memory, depth=1)
    instructions = list(_parse_instructions([call_event], call_context_manager))
    call_instruction = instructions[0]

    assert isinstance(call_instruction, CALL)
    assert call_instruction.memory_input == "2e1a7d4d000000000000000000000000000000000000000000000000016345785d8a0000"


def test_parser_updates_call_context_manager():
    root = get_root_call_context()
    manager = CallContextManager(root)
    call_target = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    stack = ["0x0", "0x4bb", "0x24", "0xb", "0x0", call_target, "0x940f"]
    memory = "00000000000000000000002e1a7d4d000000000000000000000000000000000000000000000000016345785d8a000000000000000000000000000000000000000000"

    events = [
        TraceEvent(pc=1, op=CALL.opcode, stack=stack, memory=memory, depth=1),
        TraceEvent(pc=2, op=POP.opcode, stack=["0x0"], memory="", depth=2),
    ]

    list(_parse_instructions(events, manager))

    assert manager.get_current_call_context() != root
    assert manager.get_current_call_context().code_address == call_target


def test_parser_sets_step_indexes():
    manager = get_sample_call_context_manager()
    events = [
        TraceEvent(pc=1, op=POP.opcode, stack=["0x0", "0x0"], memory=None, depth=1),
        TraceEvent(pc=2, op=POP.opcode, stack=["0x0"], memory=None, depth=1),
    ]

    pop_1, pop_2 = list(_parse_instructions(events, manager))

    assert pop_1.step_index == 0
    assert pop_2.step_index == 1
