import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=int(os.environ.get("API_PORT", "8005")),
        reload=os.environ.get("API_RELOAD", "").lower() in ("1", "true"),
    )
