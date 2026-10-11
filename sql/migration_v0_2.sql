-- PostgreSQL additive migration. Apply AFTER schema.sql on a v0.1 database.
-- All numbers below are observed OTT display numbers, never TMDB broadcast totals.
BEGIN;
ALTER TABLE anime ADD COLUMN identity_verification_status text NOT NULL DEFAULT 'review_required'
 CHECK(identity_verification_status IN ('review_required','identity_verified'));
ALTER TABLE anime ADD COLUMN identity_source_url text;
ALTER TABLE seasons ADD CONSTRAINT seasons_id_anime_unique UNIQUE(id, anime_id);

CREATE FUNCTION valid_ott_episode_numbers(numbers integer[]) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
 SELECT numbers IS NOT NULL
    AND array_position(numbers, NULL) IS NULL
    AND NOT EXISTS (SELECT 1 FROM unnest(numbers) n WHERE n < 1)
    AND cardinality(numbers) = (SELECT count(DISTINCT n) FROM unnest(numbers) n)
    AND numbers = ARRAY(SELECT n FROM unnest(numbers) n ORDER BY n);
$$;

CREATE TABLE ott_upload_snapshots (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 anime_id bigint NOT NULL REFERENCES anime(id),
 season_id bigint NOT NULL,
 ott_platform text NOT NULL REFERENCES ott_platforms(name),
 region char(2) NOT NULL DEFAULT 'KR',
 offer_type text NOT NULL DEFAULT 'unknown'
   CHECK(offer_type IN ('subscription','rental','purchase','free','unknown')),
 availability_status text NOT NULL DEFAULT 'unknown'
   CHECK(availability_status IN ('available','unavailable','unknown')),
 latest_episode_number integer CHECK(latest_episode_number > 0),
 available_episode_count integer CHECK(available_episode_count >= 0),
 available_episode_numbers integer[],
 verification_status text NOT NULL DEFAULT 'not_checked'
   CHECK(verification_status IN ('not_checked','review_required','verified','stale')),
 source_url text, verified_at timestamptz, reviewer text,
 source_method text CHECK(source_method IN ('official_manual','official_api','licensed_feed')),
 evidence_reference text,
 ott_season_label text,
 episode_numbering text NOT NULL DEFAULT 'ott_display' CHECK(episode_numbering = 'ott_display'),
 mapping_status text NOT NULL DEFAULT 'not_checked'
   CHECK(mapping_status IN ('not_checked','review_required','verified')),
 notes text,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(season_id,anime_id) REFERENCES seasons(id,anime_id),
 CONSTRAINT verified_upload_evidence CHECK (
   verification_status <> 'verified' OR (
     source_url IS NOT NULL AND source_url ~ '^https://[^/[:space:]]+'
     AND verified_at IS NOT NULL AND reviewer IS NOT NULL AND btrim(reviewer) <> ''
     AND evidence_reference IS NOT NULL AND btrim(evidence_reference) <> ''
     AND source_method IS NOT NULL AND mapping_status = 'verified'
     AND offer_type <> 'unknown' AND availability_status <> 'unknown')),
 CONSTRAINT upload_numbers_consistent CHECK (
   (verification_status <> 'verified' AND latest_episode_number IS NULL
      AND available_episode_count IS NULL AND available_episode_numbers IS NULL)
   OR (verification_status = 'verified' AND available_episode_count IS NOT NULL
      AND valid_ott_episode_numbers(available_episode_numbers)
      AND available_episode_count = cardinality(available_episode_numbers)
      AND ((availability_status = 'unavailable' AND available_episode_count = 0
              AND latest_episode_number IS NULL)
        OR (availability_status = 'available' AND available_episode_count > 0
              AND latest_episode_number IS NOT NULL
              AND latest_episode_number = (available_episode_numbers)[cardinality(available_episode_numbers)]))))
);

-- Platform splits may differ from TMDB seasons. One OTT part can map to many canonical episodes.
CREATE TABLE ott_episode_mapping (
 snapshot_id bigint NOT NULL REFERENCES ott_upload_snapshots(id),
 ott_episode_number integer NOT NULL CHECK(ott_episode_number > 0),
 canonical_episode_id bigint NOT NULL REFERENCES episodes(id),
 verification_status text NOT NULL DEFAULT 'review_required'
   CHECK(verification_status IN ('review_required','verified')),
 source_url text, verified_at timestamptz,
 PRIMARY KEY(snapshot_id,ott_episode_number,canonical_episode_id),
 CHECK(verification_status <> 'verified' OR (source_url IS NOT NULL AND verified_at IS NOT NULL))
);
CREATE INDEX idx_upload_verified ON ott_upload_snapshots(ott_platform,region,season_id,verified_at);
-- Choose the newest observation BEFORE filtering; a later unverified/stale observation hides old data.
CREATE VIEW latest_verified_ott_uploads AS
 SELECT latest.* FROM (
   SELECT DISTINCT ON (season_id,ott_platform,region,offer_type,ott_season_label) *
   FROM ott_upload_snapshots
   ORDER BY season_id,ott_platform,region,offer_type,ott_season_label,
            created_at DESC,id DESC
 ) latest JOIN anime a ON a.id = latest.anime_id
 WHERE latest.verification_status = 'verified'
   AND a.identity_verification_status = 'identity_verified'
   AND latest.verified_at >= now() - interval '7 days';
COMMIT;
