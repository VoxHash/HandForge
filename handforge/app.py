"""Application entry point for HandForge."""

import sys
from PyQt6.QtWidgets import QApplication
from .ui.main_window import MainWindow
from .util.icons import app_icon


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("HandForge")
    app.setOrganizationName("VoxHash Technologies")
    app.setWindowIcon(app_icon())

    # Discover directory + entry-point plugins before the UI builds presets.
    try:
        from .core.settings import load_settings
        from .plugins import ensure_plugins_loaded

        ensure_plugins_loaded(load_settings())
    except Exception:
        pass

    # Note: High DPI scaling is enabled by default in PyQt6
    # No need to set AA_EnableHighDpiScaling or AA_UseHighDpiPixmaps
    # System tray is owned by MainWindow (icon set before show — see util.icons).

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
