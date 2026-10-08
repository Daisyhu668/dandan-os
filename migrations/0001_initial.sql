-- Visitor-generated content is moderated by default.
CREATE TABLE IF NOT EXISTS guestbook (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nickname TEXT NOT NULL CHECK(length(nickname) <= 32),
  message TEXT NOT NULL CHECK(length(message) <= 450),
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS guestbook_status_id ON guestbook(status, id DESC);
CREATE TABLE IF NOT EXISTS rate_limits (
  key TEXT NOT NULL,
  minute INTEGER NOT NULL,
  n INTEGER NOT NULL,
  PRIMARY KEY (key, minute)
);
CREATE INDEX IF NOT EXISTS rate_limits_minute ON rate_limits(minute);
