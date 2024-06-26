from collections.abc import Iterable
from typing import Sequence

from traces_parser.parser.environment.call_context import CallContext
from traces_parser.parser.environment.call_context_manager import build_call_tree
from traces_parser.parser.environment.parsing_environment import (
    InstructionOutputOracle,
    ParsingEnvironment,
)
from traces_parser.parser.events_parser import TraceEvent
from traces_parser.parser.information_flow.constant_step_indexes import (
    SPECIAL_STEP_INDEXES,
)
from traces_parser.parser.instructions.instruction import Instruction
from traces_parser.datatypes.storage_byte_group import StorageByteGroup
from traces_parser.parser.trace_evm.trace_evm import InstructionMetadata, TraceEVM
from traces_parser.parser.transaction_parsing_info import (
    ParsedTransaction,
    TransactionParsingInfo,
)
from traces_parser.datatypes.hexstring import HexString


def parse_transaction(
    parsing_info: TransactionParsingInfo, trace_events: Iterable[TraceEvent]
) -> ParsedTransaction:
    root_call_context = _create_root_call_context(
        parsing_info.sender, parsing_info.to, parsing_info.calldata, parsing_info.value
    )

    instructions = _parse_instructions(
        trace_events, root_call_context, parsing_info.verify_storages
    )
    call_tree = build_call_tree(root_call_context, instructions)

    return ParsedTransaction(instructions, call_tree)


def _create_root_call_context(
    sender: HexString, to: HexString, calldata: HexString, value: HexString
) -> CallContext:
    return CallContext(
        parent=None,
        calldata=StorageByteGroup.from_hexstring(
            calldata, SPECIAL_STEP_INDEXES.PRESTATE
        ),
        value=StorageByteGroup.from_hexstring(value, SPECIAL_STEP_INDEXES.PRESTATE),
        depth=1,
        msg_sender=sender,
        code_address=to,
        storage_address=to,
    )


def _parse_instructions(
    events: Iterable[TraceEvent], root_call_context: CallContext, verify_storages: bool
) -> Sequence[Instruction]:
    tracer_evm = TraceEVM(ParsingEnvironment(root_call_context), verify_storages)
    events_iterator = events.__iter__()
    try:
        current_event = next(events_iterator)
    except StopIteration:
        # no events to parse
        return []

    instructions = []
    for next_event in events_iterator:
        instructions.append(
            tracer_evm.step(
                instruction_metadata=InstructionMetadata(
                    current_event.op, current_event.pc
                ),
                output_oracle=InstructionOutputOracle(
                    next_event.stack,
                    next_event.memory or HexString(""),
                    next_event.depth,
                ),
            )
        )
        current_event = next_event

    instructions.append(
        tracer_evm.step(
            instruction_metadata=InstructionMetadata(
                current_event.op, current_event.pc
            ),
            output_oracle=InstructionOutputOracle([], HexString(""), None),
        )
    )
    return instructions
