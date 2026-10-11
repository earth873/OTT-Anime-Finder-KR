-- PostgreSQL / Supabase schema (conceptual MVP). Only verified episodes are publicly shown.
CREATE TABLE anime (
 id bigint generated always as identity primary key,
 tmdb_tv_id bigint unique,
 title_ko text not null,
 title_original text,
 production_status text not null default 'unknown',
 story_completion_status text not null default 'unknown' check(story_completion_status in ('completed','ongoing','unknown')),
 first_air_date date,
 last_metadata_checked_at timestamptz
);
CREATE TABLE anime_aliases(id bigint generated always as identity primary key, anime_id bigint not null references anime(id), alias text not null, lang text,unique(anime_id,alias));
CREATE TABLE genres(id bigint generated always as identity primary key,name text unique not null);
CREATE TABLE anime_genres(anime_id bigint not null references anime(id), genre_id bigint not null references genres(id),primary key(anime_id,genre_id));
CREATE TABLE seasons(id bigint generated always as identity primary key,anime_id bigint not null references anime(id),canonical_season_number integer not null,official_status text not null default 'unknown',unique(anime_id,canonical_season_number));
CREATE TABLE episodes(id bigint generated always as identity primary key,season_id bigint not null references seasons(id),canonical_episode_number integer not null,air_date date,episode_type text not null default 'regular',unique(season_id,canonical_episode_number,episode_type));
CREATE TABLE ott_platforms(id bigint generated always as identity primary key,name text unique not null,tmdb_provider_id integer);
CREATE TABLE ott_season_catalog(
 id bigint generated always as identity primary key,
 season_id bigint not null references seasons(id),ott_id bigint not null references ott_platforms(id),
 region char(2) not null default 'KR',catalog_status text not null default 'unknown' check(catalog_status in ('available','unavailable','unknown')),
 offer_type text not null default 'unknown' check(offer_type in ('subscription','rental','purchase','unknown')),
 source_name text,source_url text,verified_at timestamptz,
 unique(season_id,ott_id,region,offer_type)
);
CREATE TABLE ott_episode_availability(
 episode_id bigint not null references episodes(id),ott_id bigint not null references ott_platforms(id),region char(2) not null default 'KR',
 availability_status text not null default 'unknown' check(availability_status in ('available','unavailable','unknown')),
 offer_type text not null default 'unknown',ott_display_episode_label text,source_name text,source_url text,verified_at timestamptz,
 primary key(episode_id,ott_id,region,offer_type)
);
CREATE TABLE verification_events(id bigint generated always as identity primary key,entity_type text not null,entity_id bigint,source_name text,source_url text,method text not null,observed_at timestamptz not null default now(),note text);
CREATE INDEX idx_ott_episode ON ott_episode_availability(ott_id,region,availability_status);
CREATE INDEX idx_seasons_anime ON seasons(anime_id);
-- Row-level security / admin access policies must be set before public deployment.
