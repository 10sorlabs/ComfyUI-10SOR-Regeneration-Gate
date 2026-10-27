# Validation record

## Unit and persistence tests

Environment:

- macOS arm64
- Python 3.12
- PyTorch 2.14.1

Command:

```bash
pytest -q
```

Result at initial publication:

```text
23 passed
```

Covered behavior:

- Lazy input declaration and decision contract
- First generation and four-slot partial regeneration
- Unlocking and replacement
- Exact tensor shape, dtype, and pixel round-trip
- Persistence through a new `ImageStore` instance
- Session and slot isolation
- Missing and corrupt state errors
- Invalid identifiers and tensors
- Atomic failed-write recovery
- Hashed runtime paths
- ComfyUI node registration

## Current ComfyUI scheduler test

ComfyUI:

- Version: `0.43.0`
- Commit: `426f5eea52a7ece1dd599fff4cb6cd1f352ddd24`
- Mode: CPU, standard server, RAM-pressure cache

The repository was symlinked into `custom_nodes`, loaded by ComfyUI, and called through the real prompt execution API. The graph contained four changing `StubConstantImage` upstream nodes, four `10SORRegenerationGate` nodes, a four-image batch, and `SaveImage`.

Observed result:

```text
preserved gates:             0  1  2  3  4
upstream nodes that ran:     4  3  2  1  0
final batch image count:     4  4  4  4  4
preserved pixels unchanged:  yes
```

This is an execution-engine test, not a mock of `check_lazy_status`: ComfyUI's WebSocket `executing` events were used to count actual upstream node execution.

## Remaining workflow-specific validation

The source carousel workflow JSON, its models, and a compatible GPU environment were not present during repository construction. The following therefore remain to be run on the target installation:

1. Insert four gates after each final enhancement and before the existing batch node.
2. Confirm no preview/save/output node independently targets a preserved image branch.
3. Run the real workflow and count KSampler node IDs in the execution log for all five lock counts.
4. Confirm the three-stage VLM remains reachable through its final prompt preview/output.
5. Restart ComfyUI with all gates preserving and confirm the final batch is produced with zero KSampler executions.
