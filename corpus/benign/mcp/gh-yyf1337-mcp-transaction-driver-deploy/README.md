# Driver Deployment Example

A simulated Windows kernel-driver deployment on a transactional MCP server. The workflow is copy driver → create service → start → verify; if any step fails, the file and service are rolled back automatically. The tools mutate an in-memory `MachineState` — swap the bodies for `vmrun` guest operations to make it real.

## Run

```bash
cd packages/examples/driver-deploy
uv run --project ../.. python client_demo.py
```

`client_demo.py` spawns the server over stdio itself and runs three scenarios:

1. A successful deployment that commits
2. A failing deployment (the service vanishes before `sc_start`) that auto-rolls back — the copied file is deleted and the transaction ends `rolled_back`
3. Checkpoint inspection — the checkpoint `sc_start` declared can be read back with `transaction_get_checkpoint`

## Tools

- `copy_driver` — compensates via `delete_file` (`dst` maps to `path`)
- `sc_create` — compensates via `sc_delete`
- `sc_start` — declares the `driver_loaded` checkpoint, no compensation (loading a kernel module has no inverse)
- `verify_driver` — read-only, raises on failed checks

The transaction tools (`transaction_status` etc.) are injected by `enable_transactions`; see the server source for the decorator declarations.
