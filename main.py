"""
NEXUS P2P: Main Application Entry Point
"""

from nexus.ui.app import MainApp


def main() -> None:
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
