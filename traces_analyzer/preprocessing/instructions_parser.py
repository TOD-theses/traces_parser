from collections.abc import Iterable

from traces_analyzer.preprocessing.call_frame_manager import CallFrameManager
from traces_analyzer.preprocessing.events_parser import TraceEvent
from traces_analyzer.preprocessing.instruction import Instruction
from traces_analyzer.preprocessing.instruction_parser import parse_instruction


def parse_instructions(events: Iterable[TraceEvent], call_frame_manager: CallFrameManager) -> Iterable[Instruction]:
    events_iterator = events.__iter__()
    try:
        current_event = next(events_iterator)
    except StopIteration:
        # no events to parse
        return []

    for next_event in events_iterator:
        instruction = parse_instruction(current_event, next_event, call_frame_manager.get_current_call_frame())
        call_frame_manager.on_step(instruction, next_event.depth)
        current_event = next_event

        yield instruction

    # NOTE: for the last event, we pass None instead of next_event
    # if this breaks something in the future (eg if the last TraceEvent is a SLOAD
    # that tries to read the stack for the result), I'll need to change this
    yield parse_instruction(current_event, None, call_frame_manager.get_current_call_frame())  # type: ignore[arg-type]