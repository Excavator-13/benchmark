# graph-forecast-data-pipeline Specification

## Purpose

Define a complete and validated conversion from the shipped Job-SDF temporal and co-occurrence Parquet files into weighted temporal graph snapshots suitable for graph forecasting.

## Requirements

### Requirement: All shipped dataset combinations can be prepared
The system SHALL prepare graph forecasting data for each of `r0`, `r1`, `r2`, `r1-region`, `r2-region`, `region`, and `company`, for both the `count` and `rate` modes. It SHALL map `count` to the shipped `dataset/demand` source and `rate` to the shipped `dataset/proportion` source, resolve repository data paths independently of the caller's working directory, and create required output directories.

#### Scenario: Prepare the default combination from a fresh checkout
- **WHEN** a user prepares `r0` in `rate` mode and no generated graph-data directory exists
- **THEN** the system reads `dataset/proportion/r0.parquet` and `dataset/graph/r0.parquet`, creates the destination directory, and emits the generated dataset without a missing-path error

#### Scenario: Prepare every supported combination
- **WHEN** a user requests preparation without restricting granularity or mode
- **THEN** the system emits data for all seven shipped granularities in both modes

#### Scenario: Reject unsupported names
- **WHEN** a user requests a granularity or mode outside the supported sets
- **THEN** the system exits with a clear validation error that lists the accepted values

### Requirement: Source graph semantics are represented explicitly
The system SHALL map graph endpoints using all context identifiers required by the selected granularity. It SHALL preserve each fully qualified source edge contribution, SHALL NOT combine occurrences from different contexts into a fabricated co-occurrence frequency, and SHALL emit edge indices with one-to-one aligned numeric weights that the loader exposes on every temporal snapshot.

#### Scenario: Context-qualified endpoints remain distinct
- **WHEN** the same skill endpoint pair occurs under two different occupation or region contexts
- **THEN** preparation maps those rows to their respective context-qualified nodes rather than merging them into one edge weight

#### Scenario: Exact source multiplicity is not discarded
- **WHEN** the same fully qualified directed edge row occurs more than once
- **THEN** the generated representation preserves the equivalent number of unit edge contributions, either as repeated aligned entries or an exactly equivalent summed weight

#### Scenario: Snapshot exposes aligned weights
- **WHEN** a generated dataset contains `E` canonical graph edges
- **THEN** every loaded snapshot contains an edge-index tensor with `E` entries and an edge-weight tensor with `E` corresponding numeric values

### Requirement: Temporal windows honor input and forecast lengths
The loader SHALL construct chronological snapshots from the generated time-by-node signal using positive `lags` and `pred_length` values. Each snapshot SHALL expose one row per node, `lags` input values per row, and `pred_length` target values per row, without crossing the end of the available timeline.

#### Scenario: Construct a multi-step forecast sample
- **WHEN** a dataset with `T` observations is loaded with `lags=6` and `pred_length=3`
- **THEN** it contains `T - 6 - 3 + 1` snapshots whose feature and target shapes are respectively `[nodes, 6]` and `[nodes, 3]`

#### Scenario: Reject an impossible window
- **WHEN** `lags` or `pred_length` is non-positive, or their sum exceeds the available observations
- **THEN** the loader raises a clear validation error before constructing snapshots

### Requirement: Data integrity failures are reported before training
Preparation and loading SHALL validate required source files, required identifier and time columns, unique node identities, graph endpoint membership, finite signal values, and structural alignment among features, targets, edges, and weights.

#### Scenario: Graph endpoint has no matching signal node
- **WHEN** a graph row references an endpoint that cannot be mapped to a node in the corresponding time series
- **THEN** preparation fails with an error identifying the dataset and unmatched endpoint instead of producing a partially mapped graph

#### Scenario: Generated data is structurally inconsistent
- **WHEN** the count of generated edge weights differs from the count of generated edges
- **THEN** loading fails before any training snapshot is returned
