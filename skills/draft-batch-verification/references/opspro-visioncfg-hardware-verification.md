# OpsPro VISIONCFG hardware verification reference

Use this reference when drafting or updating verification evidence for OpsPro `VISIONCFG` CTSP and migration work.

## CTSP hardware verification patterns

1. Start with non-destructive probes.
   - `DATE` confirms port/CTSP responsiveness.
   - `VISIONCFG` read confirms payload shape before any write.
2. For `VISIONCFG`, always capture:
   - raw request
   - raw response
   - parsed value count
   - slot interpretation (1..26 legacy/public, 27 ratio, 28..32 reserved for current 32-value contract)
3. When write tests are allowed, use this order:
   - current 32-value round-trip
   - legacy 26-value compatibility write
   - invalid ratio reject / no partial write
   - reboot persistence
   - migration from pure legacy device/state
4. After write-based evidence capture, restore baseline values and confirm readback.

## Migration verification lessons

### Exclude downgrade/re-upgrade drift from pure legacy migration evidence
If a device has already booted a newer firmware that can write a `current` `visioncfg`, then later downgrade/re-upgrade behavior is not clean REQ-005 legacy migration evidence. Treat that as a separate compatibility/schema-drift investigation, not as the primary legacy-to-current migration acceptance path.

### Pure legacy migration acceptance path
For REQ-005 migration evidence, use a device that has never been updated to the newer firmware revision being tested.

Required sequence:
1. Confirm legacy firmware returns 26-value `VISIONCFG`.
2. Write distinctive 26-value legacy test data.
3. Capture legacy readback before upgrade.
4. Upgrade to target firmware and reboot.
5. On first boot, read `VISIONCFG` and confirm:
   - 32 values total
   - slots 1..26 exactly match pre-upgrade legacy values
   - slot 27 is `10`
   - slots 28..32 are `-1/-1/-1/-1/-1`
6. Reboot via CTSP `REBOOT` and confirm current readback is unchanged.
7. Restore baseline current values after evidence capture.

### Diagnostic logging for schema issues
When investigating migration failures, instrument `_load_vision_config()` to log:
- `sizeof(struct prop_header)`
- `sizeof(struct ocv_rect)`
- `sizeof(struct _vision_config_rev0)`
- `sizeof(struct _vision_config)`
- header probe `rc`, `type`, `revision`
- current read expected size vs `rc`
- revision-0 read expected size vs `rc`

Interpretation rule:
- `current revision size mismatch (...)` followed by `vision config default` means the stored blob was interpreted as current revision but its binary size/layout did not match the current firmware's expected current schema. Do not misclassify that as successful legacy migration.

## ABI / struct-layout caution
Do not infer target firmware ABI from `PYDEBUG`-only fallback definitions or host-side binding builds. For firmware storage compatibility analysis, trust target-firmware definitions and on-device logs first.
