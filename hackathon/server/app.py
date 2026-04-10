"""OpenEnv server entrypoint."""

from api_server import app
from api_server import main as _api_main


def main():
    """Run the packaged OpenEnv server."""
    _api_main()


if __name__ == "__main__":
    main()


__all__ = ["app", "main"]
