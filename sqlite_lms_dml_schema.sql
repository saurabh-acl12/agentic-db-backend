-- SQLite version of LMS sample data
-- Uses recursive CTEs to replace generate_series()

-- ⚠️  Clear existing data first (in reverse order of dependencies)
DELETE FROM canvas_submissions;
DELETE FROM canvas_discussions;
DELETE FROM canvas_gradebook;
DELETE FROM canvas_enrolls;
DELETE FROM canvas_course;
DELETE FROM canvas_user;

-- 1️⃣  Create 100 Courses
INSERT INTO canvas_course (
  course_pk, course_sis_id, course_name, descr, start_dt, end_dt, row_created
)
WITH RECURSIVE series(g) AS (
  SELECT 1
  UNION ALL
  SELECT g + 1 FROM series WHERE g < 100
)
SELECT
  g AS course_pk,
  'COURSE-' || g AS course_sis_id,
  'Course ' || g AS course_name,
  'Description for Course ' || g,
  datetime('now', '-' || g || ' days'),
  datetime('now', '+90 days'),
  datetime('now')
FROM series;


-- 2️⃣  Create 200 Users
INSERT INTO canvas_user (
  user_sis_id, user_pk, login_id, first_name, last_name, email, row_created
)
WITH RECURSIVE series(g) AS (
  SELECT 1
  UNION ALL
  SELECT g + 1 FROM series WHERE g < 200
)
SELECT
  'USER-' || g,
  g,
  'user' || g || '@example.com',
  'First' || g,
  'Last' || g,
  'user' || g || '@example.com',
  datetime('now')
FROM series;


-- 3️⃣  Create 1000 Enrollments (spread across 100 courses)
--     Each course gets 10 users (cycled through 200)
INSERT INTO canvas_enrolls (
  course_pk, user_pk, course_sis_id, user_sis_id, role, start_dt, end_dt, row_created, enroll_status
)
WITH RECURSIVE series(r) AS (
  SELECT 1
  UNION ALL
  SELECT r + 1 FROM series WHERE r < 10
)
SELECT
  c.course_pk,
  ((c.course_pk * 10 + r) % 200) + 1 AS user_pk,
  c.course_sis_id,
  'USER-' || (((c.course_pk * 10 + r) % 200) + 1),
  CASE WHEN (ABS(RANDOM()) % 100) < 80 THEN 'Student' ELSE 'Teacher' END,
  datetime('now', '-30 days'),
  datetime('now', '+60 days'),
  datetime('now'),
  1
FROM canvas_course c
CROSS JOIN series;


-- 4️⃣  Create Gradebook items (5 per course, per enrolled user)
--     This ensures gradebook items are linked to actual enrollments
INSERT INTO canvas_gradebook (
  course_pk, user_pk, item_pk, type, type_descr, name, due_date, points_possible, row_created
)
WITH RECURSIVE series(i) AS (
  SELECT 1
  UNION ALL
  SELECT i + 1 FROM series WHERE i < 5
)
SELECT
  e.course_pk,
  e.user_pk,
  (e.course_pk * 10000 + e.user_pk * 10 + i) AS item_pk,
  'Assignment',
  'Assignment Type',
  'Assignment ' || i,
  datetime('now', '+' || i || ' days'),
  100,
  datetime('now')
FROM canvas_enrolls e
CROSS JOIN series;


-- 5️⃣  Create 100 Random Submissions
--     Ensure item_pk and user_pk come from existing gradebook entries
INSERT INTO canvas_submissions (
  submission_id, attempt_number, item_pk, user_pk, submission_dt, graded_dt, score,
  needs_submission, needs_grading, submission_url, row_created, course_pk
)
WITH RECURSIVE series(g) AS (
  SELECT 1
  UNION ALL
  SELECT g + 1 FROM series WHERE g < 100
),
random_gradebook AS (
  SELECT 
    item_pk,
    user_pk,
    course_pk,
    ROW_NUMBER() OVER (ORDER BY RANDOM()) as rn
  FROM canvas_gradebook
  LIMIT 100
)
SELECT
  s.g AS submission_id,
  1 AS attempt_number,
  rg.item_pk,
  rg.user_pk,
  datetime('now', '-' || (ABS(RANDOM()) % 10) || ' days'),
  datetime('now', '-' || (ABS(RANDOM()) % 5) || ' days'),
  ROUND((ABS(RANDOM()) % 10000) / 100.0, 2),
  0,
  0,
  'https://canvas.example.com/submission/' || s.g,
  datetime('now'),
  rg.course_pk
FROM series s
JOIN random_gradebook rg ON s.g = rg.rn;