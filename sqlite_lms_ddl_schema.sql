-- SQLite version of LMS schema
-- Note: SQLite doesn't support schemas, so 'fac.' prefix is removed
-- Triggers for auto-timestamps need to be created differently in SQLite

-- canvas_course definition

CREATE TABLE canvas_course (
	course_pk INTEGER NOT NULL PRIMARY KEY,
	course_sis_id TEXT NOT NULL,
	course_name TEXT NOT NULL,
	descr TEXT,
	start_dt TEXT,  -- SQLite uses TEXT for timestamps
	end_dt TEXT,
	grading_scale TEXT,  -- SQLite uses TEXT for JSON
	custom_attributes TEXT,
	row_created TEXT DEFAULT (datetime('now')),
	row_modified TEXT,
	fac_topic_id INTEGER,
	fac_display_name TEXT
);

CREATE INDEX canvas_course_01 ON canvas_course (course_sis_id, start_dt, end_dt);
CREATE INDEX canvas_course_02 ON canvas_course (course_pk);
CREATE INDEX canvas_course_03 ON canvas_course (course_sis_id);

-- Trigger to set row_modified on update
CREATE TRIGGER set_canvas_course_modified_timestamp 
AFTER UPDATE ON canvas_course
FOR EACH ROW
BEGIN
    UPDATE canvas_course SET row_modified = datetime('now') WHERE course_pk = NEW.course_pk;
END;


-- canvas_discussions definition

CREATE TABLE canvas_discussions (
	reply_id INTEGER NOT NULL PRIMARY KEY,
	discussion_id INTEGER NOT NULL,
	user_pk INTEGER NOT NULL,
	course_pk INTEGER NOT NULL,
	title TEXT,
	msg_start TEXT,
	msg_length INTEGER,
	posted_date TEXT,
	parent_id INTEGER,
	needs_fac_reply INTEGER,  -- SQLite uses INTEGER for boolean (0/1)
	has_fac_reply INTEGER,
	row_created TEXT DEFAULT (datetime('now')),
	row_modified TEXT,
	is_hidden INTEGER
);

CREATE INDEX canvas_discussions_course_pk_idx ON canvas_discussions (course_pk);
CREATE INDEX canvas_discussions_course_pk_user_pk_idx ON canvas_discussions (course_pk, user_pk);
CREATE INDEX canvas_discussions_user_pk_discussion_id_idx ON canvas_discussions (user_pk, discussion_id);

CREATE TRIGGER set_canvas_discussions_modified_timestamp 
AFTER UPDATE ON canvas_discussions
FOR EACH ROW
BEGIN
    UPDATE canvas_discussions SET row_modified = datetime('now') WHERE reply_id = NEW.reply_id;
END;


-- canvas_enrolls definition

CREATE TABLE canvas_enrolls (
	course_pk INTEGER NOT NULL,
	user_pk INTEGER NOT NULL,
	course_sis_id TEXT NOT NULL,
	user_sis_id TEXT NOT NULL,
	role TEXT,
	advisor_sis_id TEXT,
	start_dt TEXT,
	end_dt TEXT,
	custom_attributes TEXT,
	row_created TEXT DEFAULT (datetime('now')),
	row_modified TEXT,
	enroll_status INTEGER,
	drop_dt TEXT,
	enrollment_dt TEXT,
	sis_last_engagement_dt TEXT,
	PRIMARY KEY (course_pk, user_pk)
);

CREATE INDEX canvas_enrolls_01 ON canvas_enrolls (course_sis_id, role, enroll_status);
CREATE INDEX canvas_enrolls_02 ON canvas_enrolls (course_sis_id, role);
CREATE INDEX canvas_enrolls_course_pk_idx ON canvas_enrolls (course_pk);
CREATE INDEX canvas_enrolls_course_sis_id_idx ON canvas_enrolls (course_sis_id);
CREATE INDEX canvas_enrolls_user_sis_id_idx ON canvas_enrolls (user_sis_id);

CREATE TRIGGER set_canvas_enrolls_modified_timestamp 
AFTER UPDATE ON canvas_enrolls
FOR EACH ROW
BEGIN
    UPDATE canvas_enrolls SET row_modified = datetime('now') 
    WHERE course_pk = NEW.course_pk AND user_pk = NEW.user_pk;
END;


-- canvas_gradebook definition

CREATE TABLE canvas_gradebook (
	course_pk INTEGER NOT NULL,
	user_pk INTEGER NOT NULL,
	item_pk INTEGER NOT NULL,
	type TEXT,
	type_descr TEXT,
	type_fk INTEGER,
	name TEXT,
	description TEXT,
	due_date TEXT,
	points_possible REAL,  -- SQLite uses REAL for numeric
	score REAL,
	num_attempts REAL,
	needs_submission INTEGER,
	weighted_points REAL,
	group_id TEXT,
	item_url TEXT,
	module_title TEXT,
	grade_group REAL,
	row_created TEXT DEFAULT (datetime('now')),
	row_modified TEXT,
	position REAL,
	needs_grading INTEGER,
	PRIMARY KEY (course_pk, user_pk, item_pk)
);

CREATE INDEX canvas_gradebook_01 ON canvas_gradebook (course_pk, user_pk);
CREATE INDEX canvas_gradebook_02 ON canvas_gradebook (course_pk, user_pk, needs_submission, points_possible, due_date);
CREATE INDEX canvas_gradebook_course_pk_idx ON canvas_gradebook (course_pk, user_pk, points_possible);
CREATE INDEX canvas_gradebook_course_pk_score_idx ON canvas_gradebook (course_pk, score);
CREATE INDEX canvas_gradebook_user_item_pk_idx ON canvas_gradebook (item_pk, user_pk);

CREATE TRIGGER set_canvas_gradebook_modified_timestamp 
AFTER UPDATE ON canvas_gradebook
FOR EACH ROW
BEGIN
    UPDATE canvas_gradebook SET row_modified = datetime('now') 
    WHERE course_pk = NEW.course_pk AND user_pk = NEW.user_pk AND item_pk = NEW.item_pk;
END;


-- canvas_submissions definition

CREATE TABLE canvas_submissions (
	submission_id INTEGER NOT NULL,
	attempt_number INTEGER NOT NULL,
	item_pk INTEGER NOT NULL,
	user_pk INTEGER NOT NULL,
	submission_dt TEXT,
	graded_dt TEXT,
	score REAL,
	needs_submission INTEGER,
	needs_grading INTEGER,
	submission_url TEXT,
	row_created TEXT DEFAULT (datetime('now')),
	row_modified TEXT,
	course_pk INTEGER,
	PRIMARY KEY (submission_id, attempt_number)
);

CREATE INDEX canvas_submissions_attempt_number_idx ON canvas_submissions (attempt_number, item_pk, user_pk);
CREATE INDEX canvas_submissions_course_pk_idx ON canvas_submissions (course_pk);
CREATE INDEX canvas_submissions_item_pk_user_pk_idx ON canvas_submissions (item_pk, user_pk);
CREATE INDEX canvas_submissions_submission_id_idx ON canvas_submissions (submission_id, attempt_number, item_pk, user_pk);

CREATE TRIGGER set_canvas_submissions_modified_timestamp 
AFTER UPDATE ON canvas_submissions
FOR EACH ROW
BEGIN
    UPDATE canvas_submissions SET row_modified = datetime('now') 
    WHERE submission_id = NEW.submission_id AND attempt_number = NEW.attempt_number;
END;


-- canvas_user definition

CREATE TABLE canvas_user (
	user_sis_id TEXT NOT NULL PRIMARY KEY,
	user_pk INTEGER,
	login_id TEXT,
	alternate_id TEXT,
	pref_first_name TEXT,
	first_name TEXT,
	last_name TEXT,
	middle_name TEXT,
	email TEXT,
	phone TEXT,
	phone_country TEXT,
	phone_type TEXT,
	city TEXT,
	state TEXT,
	country TEXT,
	sex TEXT,
	birth_date TEXT,
	custom_attributes TEXT,
	row_created TEXT DEFAULT (datetime('now')),
	row_modified TEXT,
	country_code TEXT
);

CREATE INDEX canvas_user_01 ON canvas_user (user_sis_id);
CREATE INDEX canvas_user_02 ON canvas_user (user_pk);
CREATE INDEX canvas_user_login_id_idx ON canvas_user (login_id);

CREATE TRIGGER set_canvas_users_modified_timestamp 
AFTER UPDATE ON canvas_user
FOR EACH ROW
BEGIN
    UPDATE canvas_user SET row_modified = datetime('now') WHERE user_sis_id = NEW.user_sis_id;
END;


-- Foreign Key Constraints
-- Note: Foreign keys must be enabled in SQLite with: PRAGMA foreign_keys = ON;

-- For canvas_enrolls
CREATE TRIGGER fk_enroll_course_insert
BEFORE INSERT ON canvas_enrolls
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation: course_pk')
    WHERE (SELECT course_pk FROM canvas_course WHERE course_pk = NEW.course_pk) IS NULL;
END;

CREATE TRIGGER fk_enroll_user_insert
BEFORE INSERT ON canvas_enrolls
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation: user_pk')
    WHERE (SELECT user_pk FROM canvas_user WHERE user_pk = NEW.user_pk) IS NULL;
END;

-- For canvas_gradebook
CREATE TRIGGER fk_gradebook_course_insert
BEFORE INSERT ON canvas_gradebook
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation: course_pk')
    WHERE (SELECT course_pk FROM canvas_course WHERE course_pk = NEW.course_pk) IS NULL;
END;

CREATE TRIGGER fk_gradebook_user_insert
BEFORE INSERT ON canvas_gradebook
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation: user_pk')
    WHERE (SELECT user_pk FROM canvas_user WHERE user_pk = NEW.user_pk) IS NULL;
END;

-- For canvas_discussions
CREATE TRIGGER fk_discussion_course_insert
BEFORE INSERT ON canvas_discussions
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation: course_pk')
    WHERE (SELECT course_pk FROM canvas_course WHERE course_pk = NEW.course_pk) IS NULL;
END;

CREATE TRIGGER fk_discussion_user_insert
BEFORE INSERT ON canvas_discussions
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation: user_pk')
    WHERE (SELECT user_pk FROM canvas_user WHERE user_pk = NEW.user_pk) IS NULL;
END;