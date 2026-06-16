create extension if not exists "uuid-ossp";

create table if not exists profiles (
  id uuid primary key default uuid_generate_v4(),
  email text unique not null,
  full_name text,
  role text not null check (role in ('admin', 'teacher', 'student')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists student_profiles (
  id uuid primary key default uuid_generate_v4(),
  user_email text not null,
  full_name text,
  class_level text not null check (class_level in ('5', '6', '7', '8', '9', '10')),
  disability_types text[] not null default '{}',
  iq_level text not null default 'standard' check (iq_level in ('basic', 'standard', 'advanced')),
  assigned_teacher text,
  preferred_subjects text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists teacher_profiles (
  id uuid primary key default uuid_generate_v4(),
  user_email text not null,
  full_name text,
  subjects text[] not null default '{}',
  class_levels text[] not null default '{}',
  assigned_students text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists textbooks (
  id uuid primary key default uuid_generate_v4(),
  title text not null,
  class_level text not null check (class_level in ('5', '6', '7', '8', '9', '10')),
  subject text not null check (subject in ('Mathematics', 'Science', 'English', 'Social Studies', 'Hindi', 'Computer Science')),
  file_url text,
  storage_path text,
  chapters text[] not null default '{}',
  uploaded_by text,
  status text not null default 'processing' check (status in ('processing', 'ready', 'error')),
  extracted_text text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists lesson_contents (
  id uuid primary key default uuid_generate_v4(),
  textbook_id uuid references textbooks(id) on delete set null,
  chapter text not null,
  class_level text not null check (class_level in ('5', '6', '7', '8', '9', '10')),
  subject text not null,
  iq_level text not null check (iq_level in ('basic', 'standard', 'advanced')),
  content_text text,
  key_points text[] not null default '{}',
  visual_description text,
  caption_text text,
  vocabulary jsonb not null default '[]',
  animation_type text not null default 'default_concept',
  animation_script jsonb not null default '[]',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table lesson_contents
add column if not exists animation_type text not null default 'default_concept';

alter table lesson_contents
add column if not exists animation_script jsonb not null default '[]';

create table if not exists assessments (
  id uuid primary key default uuid_generate_v4(),
  student_email text not null,
  class_level text not null,
  subject text not null,
  chapter text not null,
  assessment_type text not null check (assessment_type in ('quiz', 'flashcard', 'puzzle')),
  iq_level text not null check (iq_level in ('basic', 'standard', 'advanced')),
  questions jsonb not null default '[]',
  score numeric,
  total_questions integer,
  time_spent_seconds integer,
  completed boolean not null default false,
  ai_feedback text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists textbook_chunks (
  id uuid primary key default uuid_generate_v4(),
  textbook_id uuid references textbooks(id) on delete cascade,
  class_level text,
  subject text,
  chapter text,
  chunk_index integer not null,
  content text not null,
  token_keywords text[] not null default '{}',
  page_number integer,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists video_jobs (
  id uuid primary key default uuid_generate_v4(),
  lesson_id uuid references lesson_contents(id) on delete cascade,
  status text not null default 'queued' check (status in ('queued', 'storyboard_ready', 'rendering', 'completed', 'failed', 'needs_renderer')),
  script text,
  scenes jsonb not null default '[]',
  narration_text text,
  audio_url text,
  audio_status text not null default 'pending',
  captions jsonb not null default '[]',
  video_url text,
  error_message text,
  provider_metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_textbooks_class_subject on textbooks(class_level, subject);
create index if not exists idx_lessons_lookup on lesson_contents(class_level, subject, chapter, iq_level);
create index if not exists idx_assessments_student on assessments(student_email, completed);
create index if not exists idx_students_teacher on student_profiles(assigned_teacher);
create index if not exists idx_textbook_chunks_textbook on textbook_chunks(textbook_id);
create index if not exists idx_textbook_chunks_lookup on textbook_chunks(class_level, subject, chapter);
create index if not exists idx_video_jobs_lesson on video_jobs(lesson_id);

alter table video_jobs
add column if not exists audio_url text;

alter table video_jobs
add column if not exists audio_status text not null default 'pending';

insert into profiles (email, full_name, role)
values
  ('admin@udl.local', 'Admin User', 'admin'),
  ('teacher@udl.local', 'Teacher User', 'teacher'),
  ('student@udl.local', 'Student User', 'student')
on conflict (email) do nothing;

insert into student_profiles (user_email, full_name, class_level, disability_types, iq_level, assigned_teacher, preferred_subjects)
values ('student@udl.local', 'Student User', '7', array['visual'], 'standard', 'teacher@udl.local', array['Science', 'Mathematics'])
on conflict do nothing;

insert into teacher_profiles (user_email, full_name, subjects, class_levels, assigned_students)
values ('teacher@udl.local', 'Teacher User', array['Science', 'Mathematics'], array['7', '8'], array['student@udl.local'])
on conflict do nothing;
