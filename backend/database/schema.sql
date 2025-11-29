-- === public.event_categories definition ===
-- Drop table:
-- DROP TABLE public.event_categories;

CREATE TABLE public.event_categories (
	category_id serial4 NOT NULL,
	"name" varchar(100) NOT NULL,
	CONSTRAINT event_categories_pkey PRIMARY KEY (category_id)
);

-- === public.users definition ===
-- Drop table:
-- DROP TABLE public.users;

CREATE TABLE public.users (
	user_id serial4 NOT NULL,
	email varchar(255) NOT NULL,
	password_hash text NOT NULL,
	first_name varchar(100) NULL,
	last_name varchar(100) NULL,
	"role" varchar(50) DEFAULT 'attendee'::character varying NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	major_department varchar(100) NULL,
	phone_number varchar(20) NULL,
	hobbies text NULL,
	bio text NULL,
	profile_picture text NULL,
	CONSTRAINT users_email_key UNIQUE (email),
	CONSTRAINT users_pkey PRIMARY KEY (user_id)
);

-- === public.venues definition ===
-- Drop table:
-- DROP TABLE public.venues;

CREATE TABLE public.venues (
	venue_id serial4 NOT NULL,
	"name" varchar(100) NULL,
	building varchar(100) NULL,
	room_number varchar(50) NULL,
	google_maps_link text NULL,
	CONSTRAINT venues_pkey PRIMARY KEY (venue_id)
);

-- === public.audit_log definition ===
-- Drop table:
-- DROP TABLE public.audit_log;

CREATE TABLE public.audit_log (
	log_id serial4 NOT NULL,
	user_id int4 NULL,
	"action" varchar(255) NOT NULL,
	target_type varchar(50) NULL,
	target_id int4 NULL,
	log_time timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT audit_log_pkey PRIMARY KEY (log_id),
	CONSTRAINT audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE SET NULL
);

-- === public.events definition ===
-- Drop table:
-- DROP TABLE public.events;

CREATE TABLE public.events (
	event_id serial4 NOT NULL,
	title varchar(200) NOT NULL,
	description text NULL,
	start_time timestamp NOT NULL,
	end_time timestamp NOT NULL,
	location_type varchar(20) DEFAULT 'venue'::character varying NULL,
	venue_id int4 NULL,
	custom_location_address text NULL,
	google_maps_link text NULL,
	visibility varchar(20) DEFAULT 'public'::character varying NULL,
	organizer_id int4 NULL,
	status varchar(50) DEFAULT 'upcoming'::character varying NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	created_by int4 NULL,
	CONSTRAINT events_pkey PRIMARY KEY (event_id),
	CONSTRAINT events_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id) ON DELETE CASCADE,
	CONSTRAINT events_organizer_id_fkey FOREIGN KEY (organizer_id) REFERENCES public.users(user_id) ON DELETE CASCADE,
	CONSTRAINT events_venue_id_fkey FOREIGN KEY (venue_id) REFERENCES public.venues(venue_id) ON DELETE SET NULL
);

-- === public.planning_tasks definition ===
-- Drop table:
-- DROP TABLE public.planning_tasks;

CREATE TABLE public.planning_tasks (
	task_id serial4 NOT NULL,
	event_id int4 NULL,
	title varchar(200) NOT NULL,
	description text NULL,
	status varchar(50) DEFAULT 'todo'::character varying NULL,
	priority varchar(20) DEFAULT 'medium'::character varying NULL,
	due_date timestamp NULL,
	assigned_to int4 NULL,
	created_by int4 NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	"position" float8 DEFAULT 0 NULL,
	CONSTRAINT planning_tasks_pkey PRIMARY KEY (task_id),
	CONSTRAINT planning_tasks_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES public.users(user_id) ON DELETE SET NULL,
	CONSTRAINT planning_tasks_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(user_id) ON DELETE SET NULL,
	CONSTRAINT planning_tasks_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(event_id) ON DELETE CASCADE
);
CREATE INDEX idx_planning_event_id ON public.planning_tasks USING btree (event_id);
CREATE INDEX idx_planning_position ON public.planning_tasks USING btree ("position");

-- === public.rsvps definition ===
-- Drop table:
-- DROP TABLE public.rsvps;

CREATE TABLE public.rsvps (
	user_id int4 NOT NULL,
	event_id int4 NOT NULL,
	rsvp_status varchar(50) NULL,
	CONSTRAINT rsvps_pkey PRIMARY KEY (user_id, event_id),
	CONSTRAINT rsvps_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(event_id) ON DELETE CASCADE,
	CONSTRAINT rsvps_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE
);

-- === public.event_category_map definition ===
-- Drop table:
-- DROP TABLE public.event_category_map;

CREATE TABLE public.event_category_map (
	event_id int4 NOT NULL,
	category_id int4 NOT NULL,
	CONSTRAINT event_category_map_pkey PRIMARY KEY (event_id, category_id),
	CONSTRAINT event_category_map_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.event_categories(category_id) ON DELETE CASCADE,
	CONSTRAINT event_category_map_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(event_id) ON DELETE CASCADE
);

-- === public.event_reviews definition ===
-- Drop table:
-- DROP TABLE public.event_reviews;

CREATE TABLE public.event_reviews (
	review_id serial4 NOT NULL,
	event_id int4 NOT NULL,
	user_id int4 NOT NULL,
	rating int4 NOT NULL,
	review_text text NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT event_reviews_pkey PRIMARY KEY (review_id),
	CONSTRAINT event_reviews_user_event_ukey UNIQUE (user_id, event_id),
	CONSTRAINT event_reviews_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.events(event_id) ON DELETE CASCADE,
	CONSTRAINT event_reviews_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE
);
CREATE INDEX idx_event_reviews_event_id ON public.event_reviews USING btree (event_id);