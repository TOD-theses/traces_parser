# Metadata extraction

This section describes how labels will be extracted from the traces.

## Goal

Based on the four transaction traces (2 normal, 2 reverse order), automatically determine several labels and metadata related to TOD.

!!! danger

    This does not detect if the amount of a Selfedestruct changed, as this is directly taken from the state and not stored in the stack or memory. Are there other TODs that are not visible in traces?

!!! danger

    We currently ignore, that the effects of a transaction can be reverted, either due an exceptional halt (out of gas, invalid instruction, etc.) or a normal halt (`RETURN`, `REVERT`, `STOP`, `SELFDESTRUCT`). For instance, even if a LOG statement is part of a trace, it can still be reverted. How should we handle this? Maybe as a `CallFrame.reverted` flag?

## Planned implementation

### Traces data

Here is an example for one event of an executed SLOAD instruction:

```json
{
  "pc": 1157,
  "op": 84,
  "gas": "0x1f7b1",
  "gasCost": "0x834",
  "stack": [
    "0xd0e30db0",
    "0x3d2",
    "0x62884461f1460000",
    "0xd7a8b5b72b22ea76954784721def9efafa7df99d65b759e7d1b78f9ee0094fbc",
    "0x0",
    "0x62884461f1460000",
    "0xd7a8b5b72b22ea76954784721def9efafa7df99d65b759e7d1b78f9ee0094fbc"
  ],
  "depth": 2,
  "returnData": "0x",
  "refund": "0x0",
  "memSize": "96",
  "opName": "SLOAD"
}
```

!!! warning

    The [EIP-3155](https://eips.ethereum.org/EIPS/eip-3155) also specifies an optional "memory" field. This is not included by REVM per default. However, it is necessary to understand inputs and outputs from some instructions, eg CALL and LOGx.

### Traces preprocessing

In general, we try not to load the whole trace into the memory. To achieve this goal, we iterate through the lines and process them on the go. Between each processing step we only pass the necessary data forward and forget all irrelevant data.

#### Map each JSON to a `TraceEvent`

This step simply maps a trace event from JSON to a python class (`TraceEvent`).

Currently this is only implemented for traces generated with REVM (based on EIP-3155). However, new implementations could map other traces formats to `TraceEvent`, as long as the necessary information is included in the trace.

#### Parse `Instruction`s

We start the process with an initial `CallFrame`, which stores who created the transaction and which contract/EOA is called.

Then we iterate through the `TraceEvent`s, always looking at two successive `TraceEvent`s. Based on these events we create an `Instruction` object, which specifies the EVM instruction, its inputs and also its outputs. For some instructions the currently executed contract is important, so we link the current `CallFrame` to it. For instance, a `SLOAD` instruction loads the data from the current contracts storage.

If we encounter a `CALL` we create a new `CallFrame`, or on a `RETURN` we go back to the previous one. To be sure, we also check if the `depth` parameter changes. If it changes, thought the instruction is neither `CALL` or `RETURN`, we raise an Exception.

The `Instruction` includes:

- opcode
- program_counter
- call_frame
- [stack_inputs] (if it's a `StackInstruction`)
- [stack_outputs] (if it's a `StackInstruction`)
- [additional fields based on the instruction type, eg `key` for `SLOAD`]

!!! warning

    How should we treat inputs/outputs from/to non-stack? in particular, the memory for eg calls?

!!! warning

    How should the `CallFrame` for `DELEGATECALL` be implemented? Split into `code_address` and `storage_address`?

#### Create `EnvironmentChange`s

Based on two successive `TraceEvent`s, compute the change between the environments. This includes following changes:

- `StackChange`
- `MemoryChange`
- `ProgramCounterChange`
- `CallDepthChange` (?)
- `ReturnDataChange` (?)

## Analysis

### Instruction effect changes

To understand, where the TOD occurs we compare the transaction trace from both cases. At each iteration, we compare the `EnvironmentChange`s of both traces. The first time they differ, is the point at which the same instruction had a different effect.

This could happen at a `SLOAD` if the storage is influenced by the other transaction, a `BALANCE`, etc. This detection will simply report the instruction that was executed before the traces diverge.

**Requires**:

- comparison of two traces
- access to `EnvironmentChange`s
- access to `Instruction`s

**Labels**:

- TOD-source-instruction

!!! warning

    Check if this also works for reverts.

!!! note

    There could be multiple instructions that are directly affected by the previous transaction, however for all but the first instruction, it is hard to differentiate between a direct effect of the previous transaction, or an indirect effect through the first divergent instruction.

!!! note

    The same could be achieved by looking at the instruction outputs. However, this would require an exact modelling of all instruction outputs. Checking the stack, memory and pc is easier and less error-prone.

### Instruction input changes

To understand, which instructions are affected by the TOD, we compare if the same instructions were executed, and if they were given the same inputs.

Create a counter that counts how often an instruction has been called. An instruction is identified by (pc, inputs). For instructions in trace A, increment it. For instructions in the other trace, decrement it.

**Requires**:

- comparison of two traces
- access to `Instruction`s

**Labels**:

- TOD-Amount, TOD-Recipient, TOD-Transfer, TOD-Selfdestruct
- ether profits
- list of affected instructions

If this includes inputs from the memory, further:

- call input changes
- log changes
- token profits (through log changes)

### Instruction usage

We record all executed unique instructions, eg to understand if hashing was used. We group this by the contract address that executed them.

**Requires**:

- access to `Instruction`s
- access to `CallFrame`s

**Labels**:

- cryptography usage (hashing, signatures)
- usage of recently introduce opcodes

!!! warning

    Solidity uses `keccak256` internally for mappings. Some detection tools based on the source code may understand Solidity mappings, but not usage of `keccak256` in other cases.

## Not yet covered

- usage of precompiled contracts (see [https://www.evm.codes/precompiled](https://www.evm.codes/precompiled))
- attacker-preconditions (eg. if the address from the attacker was returned from a SLOAD or a SLOAD with the attackers address as index returned != 0? Maybe hard to understand without information flow analysis)
- control flow differences (where and through what? implement eg with changes or by comparing instructions)
- attack symmetry (if the order was different, would the "victim" be an "attacker"?)