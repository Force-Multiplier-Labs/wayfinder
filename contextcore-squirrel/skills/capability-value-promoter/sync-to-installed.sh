#!/bin/bash
# Sync skill from development folder to installed location
# Run from project root: ./sync-to-installed.sh

SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="$HOME/.claude/skills/capability-value-promoter"

echo "Syncing capability-value-promoter skill..."
echo "  From: $SOURCE_DIR"
echo "  To:   $TARGET_DIR"

# Sync SKILL.md
cp "$SOURCE_DIR/SKILL.md" "$TARGET_DIR/"

# Sync references
cp "$SOURCE_DIR/references/"* "$TARGET_DIR/references/"

# Sync scripts
cp "$SOURCE_DIR/scripts/"* "$TARGET_DIR/scripts/"

echo "Done. Skill synced to installed location."
