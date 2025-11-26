"""Application entry point for HandForge."""

import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QTimer
from .ui.main_window import MainWindow


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("HandForge")
    app.setOrganizationName("VoxHash Technologies")
    
    # Note: High DPI scaling is enabled by default in PyQt6
    # No need to set AA_EnableHighDpiScaling or AA_UseHighDpiPixmaps
    
    # System tray icon (if supported)
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray_icon = QSystemTrayIcon()
        # Use a simple icon or create one
        # For now, just set a tooltip
        tray_icon.setToolTip("HandForge - Audio & Video Converter")
        
        # Create tray menu
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show Window")
        quit_action = tray_menu.addAction("Quit")
        tray_icon.setContextMenu(tray_menu)
        tray_icon.show()
        
        def show_window():
            window.show()
            window.raise_()
            window.activateWindow()
        
        def quit_app():
            app.quit()
        
        show_action.triggered.connect(show_window)
        quit_action.triggered.connect(quit_app)
        tray_icon.activated.connect(lambda reason: show_window() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

