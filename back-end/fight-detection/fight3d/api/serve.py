from __future__ import annotations

import uvicorn

from fight3d.api.main import create_app
from fight3d.settings_yaml import load_settings


def main() -> None:
    s = load_settings()
    app = create_app()
    uvicorn.run(
        app,
        host=str(s.api.host),
        port=int(s.api.port),
        log_level=str(s.api.log_level),
    )


if __name__ == "__main__":
    main()
