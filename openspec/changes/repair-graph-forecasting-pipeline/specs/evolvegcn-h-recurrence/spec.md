## Purpose

Define the recurrent weight semantics and lifecycle boundaries required for the graph model to behave as EvolveGCN-H while remaining trainable and reproducible.

## ADDED Requirements

### Requirement: Graph-convolution weights evolve across snapshots
For the first snapshot of a sequence, EvolveGCN-H SHALL derive its graph-convolution weight from the learnable initial weight. For every later snapshot in that sequence, it SHALL use the weight state produced by the immediately preceding snapshot, and SHALL expose the newly produced state to the sequence runner.

#### Scenario: First snapshot uses the learned initial state
- **WHEN** a sequence begins without a prior recurrent weight state
- **THEN** the first GRU update receives the model's learnable initial weight

#### Scenario: Later snapshot uses the prior evolved state
- **WHEN** a second snapshot is evaluated with the state returned by the first snapshot
- **THEN** the second GRU update receives that returned state rather than the unchanged initial weight

### Requirement: Initial weight remains trainable
The learnable initial weight SHALL remain connected to automatic differentiation during training and SHALL receive a gradient when a sequence loss is backpropagated through the first recurrent update.

#### Scenario: Backpropagation reaches initial weight
- **WHEN** a training loss that depends on an EvolveGCN-H output is backpropagated
- **THEN** the initial weight parameter has a finite, non-null gradient

### Requirement: Recurrent state has explicit sequence boundaries
The experiment runner SHALL initialize EvolveGCN-H recurrent weight state at the start of every train, validation, and test traversal, carry it only between chronological snapshots within that traversal, and prevent state from persisting implicitly on the model between traversals.

#### Scenario: State carries within one traversal
- **WHEN** consecutive snapshots from one split are processed in chronological order
- **THEN** each snapshot after the first receives the state produced by its predecessor

#### Scenario: State resets between traversals
- **WHEN** validation starts after training, a new epoch starts, or final testing starts after checkpoint loading
- **THEN** that traversal begins from the model's initial weight and not from state left by the prior traversal

### Requirement: Recurrent state follows execution device
Any recurrent weight state accepted or returned during a sequence SHALL be compatible with the model and snapshot device without relying on an unregistered mutable tensor stored on the model.

#### Scenario: CUDA sequence execution
- **WHEN** the model and snapshots execute on a CUDA device
- **THEN** the initial and evolved recurrent weight states are on that same CUDA device

