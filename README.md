# 10SOR Regeneration Gate for ComfyUI

`10SOR Regeneration Gate` lets a ComfyUI carousel workflow regenerate only the selected image slots. Each gate sits after one complete generation/enhancement branch and directly before the final image batching node.

- `regenerate = TRUE`: ComfyUI evaluates the lazy image input, the branch runs, and the successful result replaces that slot's saved tensor.
- `regenerate = FALSE`: the lazy image input is not requested, the branch is skipped, and the last saved tensor is returned.

The extension uses one gate per slot, no frontend JavaScript, no database, and no changes to ComfyUI core.

## Install

```bash
cd /workspace/ComfyUI/custom_nodes
git clone https://github.com/10sorlabs/ComfyUI-10SOR-Regeneration-Gate.git
```

Restart ComfyUI. Search for **10SOR Regeneration Gate** under the `10sorLabs` category.

The extension has no additional package requirements. It uses PyTorch and `folder_paths`, which are already part of a normal ComfyUI installation.

## Update

```bash
cd /workspace/ComfyUI/custom_nodes/ComfyUI-10SOR-Regeneration-Gate
git pull
```

Restart ComfyUI after updating.

## Connect four carousel slots

For each slot, insert one gate after the last operation that should be skipped and before `Batch Images`:

```text
Extract prompt -> image edit -> KSampler -> VAE Decode -> enhancement
                                                            |
                                                            v
                                              10SOR Regeneration Gate
                                                            |
                                                            v
                                                       Batch Images
```

Configure the four gates as follows:

| Gate | `session_id` | `slot_id` |
|---|---|---:|
| Slot 1 | Same shared carousel ID | 1 |
| Slot 2 | Same shared carousel ID | 2 |
| Slot 3 | Same shared carousel ID | 3 |
| Slot 4 | Same shared carousel ID | 4 |

On a new session, run all four gates with `regenerate = TRUE` once. After that, set approved slots to `FALSE` and leave only the slots that need a new image on `TRUE`.

Changing `session_id` starts an isolated carousel. A preserved slot with no saved image fails with a clear message instead of silently spending GPU time.

## Controls

| Input | Meaning |
|---|---|
| `fresh_image` | Lazy IMAGE connection from the end of one generation branch |
| `regenerate` | `TRUE` evaluates and stores the branch; `FALSE` restores the saved image |
| `session_id` | Shared identifier for one carousel; change it for a new carousel |
| `slot_id` | Unique slot number, 1 through 4 |

The single output connects to the corresponding input of the existing `Batch Images` node.

## Why the upstream KSampler is skipped

ComfyUI normally evaluates all inputs before executing a node. This extension marks `fresh_image` as a lazy input and implements `check_lazy_status` according to the official [Lazy Evaluation documentation](https://docs.comfy.org/custom-nodes/backend/lazy_evaluation).

When `regenerate` is `FALSE`, `check_lazy_status` returns no required lazy inputs. The scheduler therefore has no execution dependency on that slot's generation branch. The stored image is loaded locally and the batch still receives a valid IMAGE tensor.

The branch must not feed another active output node. If a preview or save node is connected inside the image branch, that separate output can still cause the branch to execute. Remove or mute those image-side outputs when validating selective regeneration.

The three-stage VLM can remain active through its own final-text preview/output. Image gates do not lock prompts; they only remove locked image branches from that execution.

## Requesting another variation

ComfyUI caches unchanged upstream work. To request a genuinely new generation, change the existing variation-planner seed or another intended generation input before queueing the workflow. Switching `regenerate` to `TRUE` makes the branch eligible; it does not deliberately defeat ComfyUI's cache when every upstream input is identical.

This is intentional: unconditional `NaN` cache invalidation would be wasteful and still would not provide a meaningful new variation without a changed seed.

## Persistent image storage

Images are stored as lossless PyTorch tensors under:

```text
<ComfyUI user directory>/10sor_regeneration_gate/
```

Session and slot values are SHA-256 hashed before becoming path components. Each file includes the original identifiers, format version, tensor shape, dtype, and exact pixel values. Writes use a temporary file, `fsync`, and atomic replacement where the operating system supports it. A failed write leaves the previous successful image in place.

To relocate storage, set `TEN_SOR_REGEN_GATE_STORAGE_DIR` before starting ComfyUI:

```bash
export TEN_SOR_REGEN_GATE_STORAGE_DIR=/workspace/comfyui-state/10sor-gates
python main.py
```

Use persistent disk storage on RunPod. Deleting the directory removes the saved slot images; it does not alter workflow JSON.

## Verifying sampler skipping

Enable normal ComfyUI execution logging, run all four slots once, then repeat with selected gates set to `FALSE`. In the second run, locked branch node IDs must not appear as executing nodes. Expected sampler executions are:

| Preserved slots | Expected KSampler executions |
|---:|---:|
| 0 | 4 |
| 1 | 3 |
| 2 | 2 |
| 3 | 1 |
| 4 | 0 |

These counts assume no other active output depends on a preserved branch.

## Troubleshooting

### “has no stored image”

Set that gate to `TRUE` and run it once for the current `session_id` and `slot_id`. Do not copy an old session ID into a new carousel unless reusing its images is intentional.

### A preserved KSampler still executes

Check for preview/save/output nodes attached to that image branch. Any active output creates an independent reason to execute it. The gate must be after all work that should be skipped and immediately before batching.

### The VLM does not produce new prompts

Keep the existing final-prompt preview/output reachable and change the variation-planner seed. The image gate intentionally does not force or duplicate the VLM.

### Stored state is corrupt or unreadable

The node reports the exact affected session/slot file. Set the slot to `TRUE` and queue a successful generation to replace it. If the corrupt file prevents that workflow from loading, remove only the reported `.pt` file, then regenerate that slot.

### Multiple workflows reuse an image unexpectedly

Give concurrent or unrelated workflows different `session_id` values. Gates intentionally share state when both `session_id` and `slot_id` match.

## Tests

From the repository root, in a Python environment that has PyTorch:

```bash
python -m pip install pytest
pytest
```

The automated suite covers exact tensor round-trips, four-slot behavior, session isolation, persistence across store instances, atomic failure recovery, corrupt/missing state, lazy-input decisions, unlocking, and node registration.

### Current ComfyUI execution validation

The node was loaded as a real custom extension in ComfyUI `0.43.0` at upstream commit `426f5eea52a7ece1dd599fff4cb6cd1f352ddd24` and exercised through ComfyUI's HTTP/WebSocket execution API in CPU mode.

The validation graph used four independently changing upstream IMAGE test nodes, four regeneration gates, three built-in `ImageBatch` nodes, and `SaveImage`. After initialization, the observed upstream execution counts were:

| Preserved gates | Observed upstream executions |
|---:|---:|
| 0 | 4 |
| 1 | 3 |
| 2 | 2 |
| 3 | 1 |
| 4 | 0 |

The final batch contained four images in every case, and preserved outputs were pixel-identical. A separate restart-style storage test loads saved tensors through a new store instance.

This validates ComfyUI's real lazy graph scheduling for the node without requiring model downloads. Actual GPU KSampler log validation still requires the target workflow, models, and GPU runtime. Do not infer that workflow-specific outputs are disconnected merely from matching final images; verify the executed node IDs as described above.

## Workflow integration status

The extension is ready to insert, but a modified workflow JSON is intentionally not included until the source carousel workflow is supplied. Node IDs, link IDs, group geometry, and existing output dependencies must be inspected rather than guessed.
