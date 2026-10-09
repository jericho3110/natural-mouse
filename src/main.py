"""Entry point for the natural_mouse toolkit.

Wires the concrete strategies (Win32InputExecutor, TemplateMatchLocator,
BezierPathGenerator) together into a UIAutomator and exposes it as a small
CLI, or launches the GUI if run with no arguments. Either way this is a
manual tool: each action (a CLI command, or a button press in the GUI)
happens because you triggered it, then it's done — there is no loop or
scheduler anywhere in this codebase.

Usage:
    python main.py                        # launch the GUI
    python main.py click templates/target.png
    python main.py click templates/target.png --confidence 0.9 --region 0 0 1920 1080
    python main.py scroll --amount 5      # scroll up 5 notches (wherever the cursor already is)
    python main.py scroll --amount -5     # scroll down 5 notches
    python main.py scroll --amount -5 --at 800 500   # move there first, then scroll
    python main.py capture --region 0 0 200 100 --output templates/target.png
    python main.py testbench              # live test run on a local page (see docs/TESTBENCH.md)
    python main.py testbench --no-open    # print the page URL instead of opening the browser
    python main.py pathlab                # compare movement variants: table + pathlab.png (no mouse)
"""

from __future__ import annotations

import argparse
import sys
import webbrowser

from natural_mouse import (
    BezierPathGenerator,
    ColorLocator,
    MovementProfile,
    Point,
    TemplateMatchLocator,
    UIAutomator,
    Win32InputExecutor,
    capture_region,
)


def build_automator(profile: MovementProfile | None = None) -> UIAutomator:
    """Composition root: the one place concrete classes are chosen. Every
    other module only ever sees the abstract interfaces."""
    return UIAutomator(
        locator=TemplateMatchLocator(),
        executor=Win32InputExecutor(),
        path_generator=BezierPathGenerator(profile),
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manually trigger one natural-mouse action and exit, or launch the GUI with no arguments.",
    )
    subparsers = parser.add_subparsers(dest="command")

    click_parser = subparsers.add_parser("click", help="Find a UI element on screen and click it.")
    click_parser.add_argument("template", help="Path to the reference image of the element to find.")
    click_parser.add_argument("--confidence", type=float, default=0.85, help="Match confidence threshold (0-1).")
    click_parser.add_argument(
        "--region",
        type=int,
        nargs=4,
        metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"),
        default=None,
        help="Restrict the search to a screen region instead of the whole screen.",
    )

    scroll_parser = subparsers.add_parser("scroll", help="Scroll the mouse wheel once.")
    scroll_parser.add_argument(
        "--amount",
        type=int,
        required=True,
        help="Wheel notches: positive scrolls up, negative scrolls down.",
    )
    scroll_parser.add_argument("--steps", type=int, default=5,
                               help="Number of smaller nudges to split the scroll into.")
    scroll_parser.add_argument(
        "--at",
        type=int,
        nargs=2,
        metavar=("X", "Y"),
        default=None,
        help="Move the cursor to this screen point before scrolling. Windows sends wheel "
             "events to whatever is under the cursor, so without this the scroll happens "
             "wherever the cursor already is (often not what you want).",
    )

    capture_parser = subparsers.add_parser("capture", help="Save a screen region as a template image.")
    capture_parser.add_argument(
        "--region",
        type=int,
        nargs=4,
        required=True,
        metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"),
        help="Screen region to capture.",
    )
    capture_parser.add_argument("--output", required=True, help="Path to save the captured image to.")

    bench_parser = subparsers.add_parser(
        "testbench",
        help="Open a local test page and check clicks and scrolls against what the browser receives.",
    )
    bench_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Print the page URL instead of opening the default browser (open it in any browser yourself).",
    )

    lab_parser = subparsers.add_parser(
        "pathlab", help="Compare movement variants (curves, easing, jitter, Fitts): a table and a picture.")
    lab_parser.add_argument("--out", default="pathlab.png", help="Where to save the picture (PNG).")
    lab_parser.add_argument("--runs", type=int, default=25, help="Paths generated per variant.")
    lab_parser.add_argument("--seed", type=int, default=1, help="Random seed: the same seed gives the same paths.")

    return parser.parse_args(argv)


def run_click(automator: UIAutomator, args: argparse.Namespace) -> int:
    region = tuple(args.region) if args.region else None
    found = automator.find_and_click(args.template, region=region, confidence=args.confidence)

    if found:
        print(f"Found and clicked target: {args.template}")
        return 0

    print(f"Target not found above confidence {args.confidence}: {args.template}")
    return 1


def run_scroll(automator: UIAutomator, args: argparse.Namespace) -> int:
    at = Point(*args.at) if args.at else None
    automator.scroll(args.amount, steps=args.steps, at=at)
    direction = "up" if args.amount > 0 else "down"
    print(f"Scrolled {direction} {abs(args.amount)} notch(es).")
    return 0


def run_capture(args: argparse.Namespace) -> int:
    capture_region(tuple(args.region), args.output)
    print(f"Saved capture to: {args.output}")
    return 0


def run_testbench(args: argparse.Namespace) -> int:
    # Imported here so the click/scroll/capture commands don't load the
    # bench (and its web server) when they don't need it.
    from testbench import run_bench

    executor = Win32InputExecutor()
    automator = UIAutomator(
        locator=ColorLocator(),
        executor=executor,
        path_generator=BezierPathGenerator(),
    )
    opener = (lambda url: print(f"Open this URL in a browser: {url}")) if args.no_open else webbrowser.open
    return run_bench(automator, executor.get_cursor_position, opener=opener)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.command is None:
        from gui import main as run_gui
        run_gui()
        return 0

    if args.command == "capture":
        return run_capture(args)
    if args.command == "testbench":
        return run_testbench(args)
    if args.command == "pathlab":
        from pathlab import run as run_pathlab  # only loaded for this command
        return run_pathlab(out=args.out, runs=args.runs, seed=args.seed)

    automator = build_automator()
    if args.command == "click":
        return run_click(automator, args)
    if args.command == "scroll":
        return run_scroll(automator, args)

    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
