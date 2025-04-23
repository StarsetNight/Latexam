BEGIN TRANSACTION;

CREATE TABLE "Student" (
	"Uid"	TEXT NOT NULL UNIQUE,
	"Nickname"	TEXT NOT NULL,
	"Password"	TEXT NOT NULL,
	PRIMARY KEY("Uid")
);

CREATE INDEX "Uid" ON "Student" (
	"Uid"
);

PRAGMA journal_mode=WAL;

COMMIT;