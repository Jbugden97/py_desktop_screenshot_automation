"""Desktop screenshot automation package."""


def main() -> None:
    """Launch the desktop application."""
    from .app import run_app

    run_app()


__all__ = ["main"]
