"""Entry point so `python -m bird_watcher` works."""

from . import __version__


def main() -> None:
    print(f"bird-watcher v{__version__}")
    print("Built in 10 issues. See README.md.")


if __name__ == "__main__":
    main()