CREATE TABLE departments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('Employee','Organizer','Admin')),
  department_id INTEGER NOT NULL REFERENCES departments(id),
  is_active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  start_time TEXT NOT NULL,              -- 'YYYY-MM-DD HH:MM'
  location TEXT NOT NULL,
  department_id INTEGER NOT NULL REFERENCES departments(id),  -- phòng ban tổ chức
  organizer_id INTEGER NOT NULL REFERENCES users(id),
  max_participants INTEGER NOT NULL CHECK (max_participants > 0),
  registration_deadline TEXT NOT NULL,
  target_department_id INTEGER REFERENCES departments(id),    -- NULL = toàn công ty (BR07)
  status TEXT NOT NULL DEFAULT 'Open' CHECK (status IN ('Open','Cancelled'))
);
CREATE TABLE registrations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id INTEGER NOT NULL REFERENCES events(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  status TEXT NOT NULL DEFAULT 'Registered'
         CHECK (status IN ('Registered','Confirmed','Attended','Cancelled')),
  created_at TEXT NOT NULL,
  UNIQUE (event_id, user_id)             -- BR01
);
