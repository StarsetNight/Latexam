from pathlib import Path
from aiofiles import open as aopen

async def get_sql_script(path: Path) -> str:
    async with aopen(path, "r") as f:
        return await f.read()