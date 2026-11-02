import sys
from ui.application import Application


def main() -> int:
    app = Application(sys.argv)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())