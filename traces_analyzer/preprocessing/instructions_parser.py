from collections.abc import Iterable
from typing import TypeGuard

from traces_analyzer.preprocessing.call_frame import CallFrame
from traces_analyzer.preprocessing.events_parser import TraceEvent
from traces_analyzer.preprocessing.instructions import (
    CALL,
    CALLCODE,
    DELEGATECALL,
    RETURN,
    REVERT,
    SELFDESTRUCT,
    STATICCALL,
    STOP,
    Instruction,
    parse_instruction,
)


def parse_instructions(events: Iterable[TraceEvent]) -> Iterable[Instruction]:
    call_frame = CallFrame(
        parent=None,
        depth=1,
        msg_sender="0x1111111111111111111111111111111111111111",
        code_address="0x1234123412341234123412341234123412341234",
        storage_address="0x1234123412341234123412341234123412341234",
    )

    events_iterator = events.__iter__()
    try:
        current_event = next(events_iterator)
    except StopIteration:
        # no events to parse
        return []

    for next_event in events_iterator:
        instruction = parse_instruction(current_event, next_event, call_frame)
        yield instruction

        call_frame = update_call_frame(call_frame, instruction, next_event.depth)
        current_event = next_event

    # NOTE: for the last event, we pass None instead of next_event
    # if this breaks something in the future (eg if the last TraceEvent is a SLOAD
    # that tries to read the stack for the result), I'll need to change this
    yield parse_instruction(current_event, None, call_frame)  # type: ignore[arg-type]


class UnexpectedDepthChange(Exception):
    pass


def update_call_frame(
    current_call_frame: CallFrame,
    instruction: Instruction,
    expected_depth: int,
):
    if current_call_frame.depth == expected_depth:
        return current_call_frame

    if enters_call_frame_normal(instruction):
        next_call_frame = CallFrame(
            parent=current_call_frame,
            depth=current_call_frame.depth + 1,
            msg_sender=current_call_frame.code_address,
            code_address=instruction.address,
            storage_address=instruction.address,
        )
    elif enters_call_frame_without_storage(instruction):
        next_call_frame = CallFrame(
            parent=current_call_frame,
            depth=current_call_frame.depth + 1,
            msg_sender=current_call_frame.code_address,
            code_address=instruction.address,
            storage_address=current_call_frame.storage_address,
        )
    elif makes_normal_halt(instruction) or makes_exceptional_halt(current_call_frame.depth, expected_depth):
        if not current_call_frame.parent:
            raise Exception(
                "Tried to return to parent call frame, while already being at the root."
                f" {current_call_frame}. {instruction}"
            )
        next_call_frame = current_call_frame.parent
    else:
        raise UnexpectedDepthChange(
            "Could not change call frame: the trace showed a change in the call depth,"
            " however the instruction should not change the depth."
            f" Expected depth change from {current_call_frame.depth} to {expected_depth}. Instruction: {instruction}."
        )

    if next_call_frame.depth != expected_depth:
        raise Exception(
            f"Unexpected call depth: CallFrame has {next_call_frame.depth},"
            f" expected {expected_depth}. {instruction}. {next_call_frame}"
        )

    return next_call_frame


def enters_call_frame_normal(instruction: Instruction) -> TypeGuard[CALL | STATICCALL]:
    return isinstance(instruction, (CALL, STATICCALL))


def enters_call_frame_without_storage(instruction: Instruction) -> TypeGuard[DELEGATECALL | CALLCODE]:
    return isinstance(instruction, (DELEGATECALL, CALLCODE))


def makes_normal_halt(instruction: Instruction) -> TypeGuard[STOP | REVERT | RETURN | SELFDESTRUCT]:
    return isinstance(instruction, (STOP, REVERT, RETURN, SELFDESTRUCT))


def makes_exceptional_halt(current_depth: int, expected_depth: int):
    return expected_depth == current_depth - 1
