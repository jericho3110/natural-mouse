# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.1] - 2026-10-09

### Fixed

- `ScreenshotOnMissPlugin`: file names are made safe (`safe_stem`) and a
  failed save raises `OSError` instead of being recorded as saved
  (colour queries like `#ff00ff`, or `:`/`*`/`?`, made Windows refuse
  the name and `cv2.imwrite` fail silently).

### Added

- The check gate `scripts/check.py` (lint, tests, links, security),
  `scripts/security_scan.py` (pip-audit, dangerous patterns, invariants;
  proven by tests/test_security_scan.py), `scripts/check_links.py`.
- GitHub Actions CI on Windows and Dependabot; `ruff.toml`; the `[dev]`
  extra (`pip install -e ".[dev]"`).
- Docs: LIBRARIES_AND_BUILTINS, GLOSSARY, FILE_TYPES; MOVEMENT.md §8.1
  (how pathlab.png is made), §8.2 (what each number means), §9 (one
  movement end to end); SECURITY.md automated checks and review findings.

### Changed

- CI upgrades pip and setuptools before installing: pip-audit found
  setuptools 65.5.0 (four advisories) on the runner's Python 3.10.
- Lint clean under the workspace's rule sets: `zip(..., strict=)` made
  explicit, shared defaults are named frozen constants.

## [0.2.0] - 2026-10-09

### Added

- **Movement building blocks**, chosen with `MovementProfile` (defaults
  keep the old behaviour): cubic Bezier curves (`curve="cubic"`),
  logistic S-curve acceleration (`easing="logistic"`,
  `logistic_steepness`), smooth tremor-like micro-jitter tapered to zero
  at both ends (`jitter_smoothing`), and Fitts's-law timing
  (`fitts=FittsLaw(a, b)`, `target_width_px`). An optional `rng` makes
  paths reproducible. See docs/MOVEMENT.md.
- **Path lab** (`python src/main.py pathlab`): compares movement
  variants as a table and a picture, without moving the mouse.
- **Extensions and plugins**, merged in from the former
  `mrfactory-mouse-ext` package: `PluggableAutomator`, retry / fallback
  / multi-scale locators, `FittsPathGenerator`,
  `RecordingPathGenerator`, `FailSafeExecutor`, and the logging, stats,
  region-guard and screenshot-on-miss plugins. Import them from
  `natural_mouse`; the plugin entry-point group is now
  `natural_mouse.plugins`.
- MIT `LICENSE`; docs/SECURITY.md.

- `python src/main.py testbench`: a live test bench that opens a local
  page, clicks and scrolls it with the real mouse, and reports what the
  browser received. See [docs/TESTBENCH.md](docs/TESTBENCH.md).
- `ColorLocator`: a `ScreenLocator` that finds solid-colour blocks
  (`"#ff00ff"`) at any zoom or DPI; `confidence` is the fill ratio.

### Fixed

- At display scaling above 100%, cursor coordinates were scaled pixels
  until the first screenshot and physical pixels after it.
  `Win32InputExecutor` now makes the process DPI-aware when it's
  created, so coordinates are always physical pixels.

## [0.1.0]

### Added

- First packaged version: `UIAutomator`, Bezier paths, Win32 input,
  template matching, CLI and Tkinter GUI.

## References

- [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/)
- [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html)
