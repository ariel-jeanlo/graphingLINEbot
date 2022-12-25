CREATE TABLE users
(
    userid VARCHAR(64) NOT NULL,
    "startdate" DATETIME NOT NULL,
    "enddate" DATETIME NOT NULL,
    title VARCHAR(64) NOT NULL,
    "location" VARCHAR(128),
    "memo" VARCHAR(1024)
);
