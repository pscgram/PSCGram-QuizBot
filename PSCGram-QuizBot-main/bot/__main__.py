
import os
from aiohttp import web
from bot.main import create_web_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    web.run_app(create_web_app(), host="0.0.0.0", port=port)
