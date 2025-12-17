# Pull Request: Downgrade OS requirement from Trixie to Bookworm and fix ReSpeaker drivers

## Summary

This PR downgrades Jasper's OS requirement from Raspberry Pi OS Trixie (Debian 13) to Bookworm (Debian 12) and fixes ReSpeaker 2-Mics HAT driver installation issues on ARM64 architecture.

## Changes

### Documentation
- Updated README.md to specify Raspberry Pi OS Bookworm (Debian 12) as the required OS

### ReSpeaker Driver Installation
- **Switched to HinTak's seeed-voicecard fork** instead of official respeaker repository
  - Official repo has kernel API compatibility issues with kernel 6.1.x+
  - HinTak's fork maintains kernel-specific branches (v6.1, v6.12, etc.) with proper fixes
- **Added automatic kernel version detection** to clone the appropriate branch
- **Added ARM64 architecture detection** to use `install_arm64.sh` on aarch64 systems
- Fixes DKMS compilation errors including:
  - `non_legacy_dai_naming` renamed to `legacy_dai_naming`
  - Missing `asoc_simple_parse_*` functions
  - i2c_driver `.remove` signature changes
  - Other kernel 6.1.x API incompatibilities

## Problem Solved

The official respeaker/seeed-voicecard repository has not been updated for newer Linux kernels. When installing on Raspberry Pi OS Bookworm (kernel 6.1.21-v8+) with ARM64 architecture, DKMS compilation would fail with multiple errors:

```
error: 'const struct snd_soc_component_driver' has no member named 'non_legacy_dai_naming'
error: implicit declaration of function 'asoc_simple_parse_cpu'
error: initialization of 'void (*)(struct i2c_client *)' from incompatible pointer type
```

These are kernel API changes between older kernels (5.x) and newer kernels (6.1+). HinTak's fork addresses all these compatibility issues with kernel-specific branches.

## Testing

Tested on Raspberry Pi 4B with:
- **OS**: Raspberry Pi OS Bookworm (Debian 12)
- **Kernel**: 6.1.21-v8+ (ARM64)
- **Hardware**: ReSpeaker 2-Mics Pi HAT

### Results
- ✅ Audio device successfully detected: `card 1: seeed2micvoicec [seeed-2mic-voicecard]`
- ✅ Jasper successfully starts and listens for wake word
- ✅ DKMS modules compile and install without errors
- ✅ No more "No audio input devices found" errors

### Log Evidence
```
2025-12-17 12:08:39,283 - root - INFO - Found input device: seeed-2mic-voicecard: bcm2835-i2s-wm8960-hifi wm8960-hifi-0 (hw:1,0)
2025-12-17 12:08:39,284 - root - INFO - Jasper assistant starting...
2025-12-17 12:08:39,569 - root - INFO - Listening for wake word...
```

## Commits

1. `f04bbff` - Downgrade OS requirement from Trixie to Bookworm
2. `897c04e` - Fix ReSpeaker driver installation for ARM64 architecture (initial)
3. `904f667` - Add diagnostic and fix scripts for ReSpeaker overlay issues
4. `12bc888` - Add configuration script for ReSpeaker boot parameters
5. `bb40e7d` - Fix ReSpeaker driver installation for ARM64 architecture (final)
6. `a683b22` - Remove temporary diagnostic scripts

Note: Commits 3-4 added temporary debugging tools that were later removed in commit 6, as the final fix in commit 5 made them unnecessary.

## Related Issues

Resolves ReSpeaker driver compatibility issues with Raspberry Pi OS Bookworm on ARM64 systems.

## Branch

- **Source**: `claude/downgrade-pios-bookworm-xhdA3`
- **Target**: `main` (or your default branch)
