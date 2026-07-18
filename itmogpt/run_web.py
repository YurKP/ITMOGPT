#!/usr/bin/env python3
import uvicorn

from app.config import cfg

if __name__ == "__main__":
    uvicorn.run(
        "app.web.api:app",
        host=cfg.WEB_HOST,
        port=cfg.WEB_PORT,
        reload=False,
    )
