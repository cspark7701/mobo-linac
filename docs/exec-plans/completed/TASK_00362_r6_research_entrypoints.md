# Task Completion Summary: Task 00361

## Summary
Use research entry points for the round6 drivers.

## Key Changes
Rename the standalone numerical and scaling drivers to the established evaluate_ research-script convention and update all imports and launcher references. Preserve the CLI-wrapper architecture guard unchanged. The initial broad run had 1,128 passes and this one naming failure; 26 focused checks now pass, along with lint. A fresh stable-code full coverage run remains required before continuation.

## Validation Results
Reviewed the scoped diff and checked whitespace before committing. Additional task-specific checks are recorded in the description above.

## Status
Completed locally. The user authorized a push after the round6 revision work is complete; no push at this step.
