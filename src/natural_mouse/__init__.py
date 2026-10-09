"""natural_mouse: human-like mouse movement, clicking, and scrolling for Windows.

Core (find something, move to it naturally, click or scroll):
    UIAutomator, BezierPathGenerator, MovementProfile, FittsLaw,
    Win32InputExecutor, TemplateMatchLocator, ColorLocator

Extensions (wrap a core strategy, so they work with plain UIAutomator):
    RetryLocator, FallbackLocator, MultiScaleTemplateLocator,
    FittsPathGenerator, RecordingPathGenerator, FailSafeExecutor

Plugins (hooks around every action; need PluggableAutomator):
    LoggingPlugin, StatsPlugin, RegionGuardPlugin, ScreenshotOnMissPlugin

See README.md and docs/.
"""

from .automator import UIAutomator
from .capture import capture_region
from .errors import ActionCancelled, FailSafeTriggered
from .extensions import (
    FailSafeExecutor,
    FallbackLocator,
    FittsPathGenerator,
    MultiScaleTemplateLocator,
    RecordingPathGenerator,
    RetryLocator,
)
from .geometry import MovementProfile, Point
from .input import InputExecutor, Win32InputExecutor
from .path import BezierPathGenerator, FittsLaw, Path, PathGenerator, PathPoint
from .pluggable import PluggableAutomator
from .plugins import (
    ActionContext,
    LoggingPlugin,
    Plugin,
    PluginManager,
    RegionGuardPlugin,
    ScreenshotOnMissPlugin,
    StatsPlugin,
)
from .vision import ColorLocator, Match, ScreenLocator, TemplateMatchLocator

__all__ = [
    # core
    "UIAutomator",
    "capture_region",
    "MovementProfile",
    "Point",
    "InputExecutor",
    "Win32InputExecutor",
    "BezierPathGenerator",
    "FittsLaw",
    "Path",
    "PathGenerator",
    "PathPoint",
    "Match",
    "ScreenLocator",
    "TemplateMatchLocator",
    "ColorLocator",
    # extensions
    "FailSafeExecutor",
    "FallbackLocator",
    "FittsPathGenerator",
    "MultiScaleTemplateLocator",
    "RecordingPathGenerator",
    "RetryLocator",
    # plugins
    "PluggableAutomator",
    "ActionContext",
    "Plugin",
    "PluginManager",
    "LoggingPlugin",
    "StatsPlugin",
    "RegionGuardPlugin",
    "ScreenshotOnMissPlugin",
    "ActionCancelled",
    "FailSafeTriggered",
]
