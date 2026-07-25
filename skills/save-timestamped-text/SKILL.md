---
name: save-timestamped-text
description: Use when the user wants to save text content to a timestamped .txt file in D:\test_skill directory
---

# Save Timestamped Text

## Overview
Save text content as a .txt file with a timestamp-based filename in `D:\test_skill`.

## When to Use
- User asks to save, write, or export text to a file
- User wants to log output, notes, or results
- Any text that needs to be persisted with a time marker

## How to Apply

1. Generate the current timestamp as filename: `YYYYMMDD_HHMMSS.txt`
2. Write the content to `D:\test_skill\<timestamp>.txt`
3. Confirm the file path to the user

## Filename Format

Use this PowerShell command to get the timestamp:

```powershell
Get-Date -Format "yyyyMMdd_HHmmss"
```

Example: `20260616_184500.txt`

## Example

User: "save this output to a file"

```powershell
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$file = "D:\test_skill\$timestamp.txt"
$content | Out-File -FilePath $file -Encoding utf8
# Confirm: saved to D:\test_skill\20260616_184500.txt
```
