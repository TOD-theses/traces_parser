from tests.test_utils.test_utils import (
    _TestCounter,
    _test_oracle,
    _test_push_steps,
    _test_root,
    assert_flow_dependencies,
)
from traces_parser.parser.environment.parsing_environment import (
    InstructionOutputOracle,
    ParsingEnvironment,
)
from traces_parser.parser.information_flow.information_flow_graph import (
    build_information_flow_graph,
)
from traces_parser.parser.instructions.instructions import (
    ADD,
    RETURN,
)
from traces_parser.parser.trace_evm.trace_evm import InstructionMetadata, TraceEVM


def test_parse_end_parses_return() -> None:
    # the evm should parse the last instruction, if it is a normal return
    root = _test_root()
    env = ParsingEnvironment(root)
    evm = TraceEVM(env, verify_storages=True)
    step_index = _TestCounter(0)

    steps: list[tuple[InstructionMetadata, InstructionOutputOracle]] = [
        *_test_push_steps(
            reversed(["0x0", "0x0"]),
            step_index,
            "push_return",
        ),
        (
            InstructionMetadata(RETURN.opcode, step_index.next("return")),
            _test_oracle(depth=None),
        ),
    ]

    instructions = [evm.step(instr, oracle) for instr, oracle in steps]
    information_flow_graph = build_information_flow_graph(instructions)

    assert_flow_dependencies(
        information_flow_graph,
        step_index,
        [
            ("return", {"push_return_0", "push_return_1"}),
        ],
    )


def test_parse_end_does_not_parse_add() -> None:
    # the evm should not fail when parsing the last instruction if it's not a return
    # eg in an out-of-gas condition
    root = _test_root()
    env = ParsingEnvironment(root)
    evm = TraceEVM(env, verify_storages=True)
    step_index = _TestCounter(0)

    steps: list[tuple[InstructionMetadata, InstructionOutputOracle]] = [
        *_test_push_steps(
            reversed(["0x1", "0x2"]),
            step_index,
            "push_add",
        ),
        (
            InstructionMetadata(ADD.opcode, step_index.next("add")),
            _test_oracle(depth=None),
        ),
    ]

    _instructions = [evm.step(instr, oracle) for instr, oracle in steps]
