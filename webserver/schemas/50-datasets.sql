drop table if exists datapoints;
drop table if exists datasets;
drop table if exists lables;

create table datasets (
  id integer primary key autoincrement,
  name text not null,
  path text not null,
  unique(name),
  unique(path)
);

create table datapoints (
  id integer primary key autoincrement,
  path text not null,
  "user_id" integer default null references users("id") on delete set default,
  "dataset_id" integer default null references datasets("id") on delete cascade
);
