import ctypes
import sys
import unittest


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class TestDpiAwareness(unittest.TestCase):
    def test_executor_makes_process_dpi_aware(self):
        # Regression (found live at 125% scaling): before the first
        # screenshot, cursor positions were scaled pixels while screenshots
        # were physical ones. Creating the executor must fix the units.
        from natural_mouse.input.win32_executor import Win32InputExecutor

        Win32InputExecutor()

        user32 = ctypes.windll.user32
        user32.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
        context = user32.GetThreadDpiAwarenessContext()
        awareness = user32.GetAwarenessFromDpiAwarenessContext(ctypes.c_void_p(context))
        self.assertNotEqual(awareness, 0)  # 0 = DPI_AWARENESS_UNAWARE


if __name__ == "__main__":
    unittest.main()
