from pathlib import Path

root = Path(__file__).parent

class SQLScript:
    InitStudentDatabase: str = (root / "InitStudentDatabase.sql").read_text(encoding="utf-8")


class SQLCommand:
    GetStudentInfo: str = (root / "./GetStudentInfo.sql").read_text(encoding="utf-8")

