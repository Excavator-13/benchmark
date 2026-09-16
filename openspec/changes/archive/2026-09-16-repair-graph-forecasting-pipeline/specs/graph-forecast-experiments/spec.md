## Purpose

Define trustworthy and repeatable graph forecasting runs whose selection, final metrics, device behavior, saved state, and documented interface agree with the experiment configuration.

## ADDED Requirements

### Requirement: Chronological splits have distinct responsibilities
The experiment SHALL split temporal snapshots chronologically into non-empty training, validation, and test partitions. It SHALL optimize parameters only on training data, select the best checkpoint only by validation loss, and evaluate the selected checkpoint on test data only after training and selection are complete.

#### Scenario: Validation improvement saves a checkpoint
- **WHEN** an epoch produces a validation loss lower than all preceding epochs
- **THEN** the experiment updates the best checkpoint using that validation result without consulting test targets

#### Scenario: Final test is isolated from selection
- **WHEN** training completes and the best validation-selected checkpoint is restored
- **THEN** the experiment traverses the test split once to write predictions, gold targets, RMSE, and MAE

#### Scenario: Split ratios produce an empty partition
- **WHEN** the available snapshot count and configured ratios would make any required partition empty
- **THEN** the experiment exits with a clear split-validation error before training

### Requirement: Every split uses the configured device
The experiment SHALL place the model, snapshot features, edge indices, edge weights, targets, and recurrent state on the configured device consistently during training, validation, and final testing.

#### Scenario: Run on a requested CUDA device
- **WHEN** a user selects an available CUDA device
- **THEN** training, validation, checkpoint restoration, and final testing complete without a CPU/CUDA tensor mismatch

#### Scenario: Requested device is unavailable
- **WHEN** a user selects a device that the runtime cannot use
- **THEN** the experiment fails before training with a clear device error

### Requirement: Seed configuration controls a single reproducible run
Each invocation SHALL execute the single integer seed supplied by the user, SHALL use that seed in the result path, and SHALL seed Python, NumPy, PyTorch CPU, and available CUDA random sources before model construction and data traversal.

#### Scenario: Requested seed is honored
- **WHEN** the experiment is invoked with `--seed 17`
- **THEN** it runs seed `17` exactly once and writes results under the seed `17` directory

#### Scenario: Identical deterministic CPU runs
- **WHEN** two CPU runs use the same inputs, configuration, seed, and deterministic settings
- **THEN** they produce matching initialized parameters and metrics within the configured numerical tolerance

### Requirement: Checkpoints are reconstructable and device-portable
The experiment SHALL save a checkpoint payload containing model parameters and the configuration required to reconstruct the model, rather than serializing the entire model object. Loading SHALL reconstruct the model, apply parameters through the state dictionary, and map tensors to the requested device.

#### Scenario: Restore on a different device class
- **WHEN** a checkpoint created on one supported device class is loaded for evaluation on another supported device class
- **THEN** model reconstruction and parameter loading succeed through explicit device mapping

#### Scenario: Checkpoint configuration does not match invocation
- **WHEN** an existing checkpoint's architecture-defining configuration conflicts with the requested evaluation configuration
- **THEN** the experiment reports the mismatch instead of silently loading incompatible parameters

### Requirement: Public commands and documentation match runtime behavior
The graph forecasting CLI and README SHALL use the same accepted option names and values. Documentation SHALL provide a valid Python 3.8 Conda command, identify preprocessing and training commands that work from a fresh checkout, accurately describe the shipped graph files without claiming an absent frequency column, state that `hidden_dim` applies only to model families that consume it, and describe the temporal split as returning train, validation, and test partitions.

#### Scenario: Follow the documented graph workflow
- **WHEN** a user follows the README from environment creation through default graph preprocessing and training
- **THEN** every documented command is syntactically accepted and resolves the shipped default dataset

#### Scenario: Inspect EvolveGCN-H CLI help
- **WHEN** a user views graph forecasting command help
- **THEN** the model option is named consistently and the help does not imply that `hidden_dim` changes EvolveGCN-H dimensions
