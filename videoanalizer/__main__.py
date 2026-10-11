"""Main application entry point for VideoAnalyzer."""

import sys


def main() -> None:
    """Launch the VideoAnalyzer FastAPI application."""
    try:
        from videoanalizer.ui.app import launch

        launch()
    except ImportError as exc:
        print(f"Error starting VideoAnalyzer: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
