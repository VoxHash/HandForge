"""Allow ``python -m handforge`` to run the headless CLI."""

from .cli import main

raise SystemExit(main())
