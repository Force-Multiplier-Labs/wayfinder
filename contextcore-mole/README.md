# contextcore-mole

CLI tool to recover tasks from ContextCore Tempo trace exports.

## Installation

```bash
pip install contextcore-mole
```

## Usage

```bash
# Scan trace exports for tasks
mole scan <trace-export.json>

# List tasks
mole list <file.json> --status cancelled

# Show task details
mole show <file.json> <task-id>

# Export for re-import
mole export <file.json> --status cancelled -o recovered.json
```

## Related

Part of the [ContextCore](https://github.com/contextcore) ecosystem.
