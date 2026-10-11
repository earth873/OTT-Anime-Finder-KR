-- Apply after schema.sql and migration_v0_2.sql, only on an isolated test DB first.
BEGIN;

ALTER TABLE ott_upload_snapshots ADD CONSTRAINT upload_observed_time
 CHECK(verified_at IS NULL OR verified_at <= created_at);

CREATE FUNCTION enforce_ott_mapping() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE snapshot_anime bigint; episode_anime bigint; observation integer[];
BEGIN
 SELECT snap.anime_id,s.anime_id,snap.available_episode_numbers
 INTO snapshot_anime,episode_anime,observation
 FROM ott_upload_snapshots snap
 CROSS JOIN episodes e JOIN seasons s ON s.id=e.season_id
 WHERE snap.id=NEW.snapshot_id AND e.id=NEW.canonical_episode_id
 FOR SHARE OF snap,e,s;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'mapping snapshot or episode does not exist' USING ERRCODE='23503';
 END IF;
 IF snapshot_anime <> episode_anime THEN
   RAISE EXCEPTION 'mapping crosses anime identities' USING ERRCODE='23514';
 END IF;
 IF NEW.verification_status='verified' AND (
    observation IS NULL OR NOT NEW.ott_episode_number=ANY(observation)
    OR NEW.source_url IS NULL OR btrim(NEW.source_url)=''
    OR NEW.verified_at IS NULL OR NEW.verified_at > now()) THEN
   RAISE EXCEPTION 'verified mapping lacks observed number or evidence' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER enforce_mapping BEFORE INSERT OR UPDATE ON ott_episode_mapping
 FOR EACH ROW EXECUTE FUNCTION enforce_ott_mapping();

-- Avoid invalidating mappings through later parent changes.
CREATE FUNCTION protect_ott_mapping_parents() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME='ott_upload_snapshots' THEN
   IF NEW.anime_id IS DISTINCT FROM OLD.anime_id AND EXISTS(
       SELECT 1 FROM ott_episode_mapping WHERE snapshot_id=OLD.id) THEN
     RAISE EXCEPTION 'mapped snapshot identity cannot change' USING ERRCODE='23514';
   END IF;
   IF EXISTS(SELECT 1 FROM ott_episode_mapping m WHERE m.snapshot_id=OLD.id
       AND m.verification_status='verified'
       AND (NEW.available_episode_numbers IS NULL OR NOT m.ott_episode_number=ANY(NEW.available_episode_numbers))) THEN
     RAISE EXCEPTION 'snapshot would invalidate verified mapping' USING ERRCODE='23514';
   END IF;
 ELSIF TG_TABLE_NAME='episodes' THEN
   IF NEW.season_id IS DISTINCT FROM OLD.season_id AND EXISTS(
       SELECT 1 FROM ott_episode_mapping WHERE canonical_episode_id=OLD.id) THEN
     RAISE EXCEPTION 'mapped canonical episode season cannot change' USING ERRCODE='23514';
   END IF;
 ELSIF TG_TABLE_NAME='seasons' THEN
   IF NEW.anime_id IS DISTINCT FROM OLD.anime_id AND EXISTS(
       SELECT 1 FROM episodes e JOIN ott_episode_mapping m ON m.canonical_episode_id=e.id
       WHERE e.season_id=OLD.id) THEN
     RAISE EXCEPTION 'mapped canonical season anime cannot change' USING ERRCODE='23514';
   END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER protect_snapshot_mappings BEFORE UPDATE ON ott_upload_snapshots
 FOR EACH ROW EXECUTE FUNCTION protect_ott_mapping_parents();
CREATE TRIGGER protect_episode_mappings BEFORE UPDATE ON episodes
 FOR EACH ROW EXECUTE FUNCTION protect_ott_mapping_parents();
CREATE TRIGGER protect_season_mappings BEFORE UPDATE ON seasons
 FOR EACH ROW EXECUTE FUNCTION protect_ott_mapping_parents();

-- Existing invalid mappings must be corrected manually, never silently removed.
DO $$
BEGIN
 IF EXISTS(SELECT 1 FROM ott_episode_mapping m JOIN ott_upload_snapshots snap ON snap.id=m.snapshot_id
   JOIN episodes e ON e.id=m.canonical_episode_id JOIN seasons s ON s.id=e.season_id
   WHERE snap.anime_id<>s.anime_id OR (m.verification_status='verified' AND (
     snap.available_episode_numbers IS NULL OR NOT m.ott_episode_number=ANY(snap.available_episode_numbers)
     OR btrim(m.source_url)='' OR m.verified_at>now()))) THEN
   RAISE EXCEPTION 'existing mapping needs manual correction before migration' USING ERRCODE='23514';
 END IF;
END $$;
CREATE OR REPLACE VIEW latest_verified_ott_uploads AS
 SELECT latest.* FROM (
   SELECT DISTINCT ON (season_id,ott_platform,region,offer_type,ott_season_label) *
   FROM ott_upload_snapshots
   ORDER BY season_id,ott_platform,region,offer_type,ott_season_label,created_at DESC,id DESC
 ) latest JOIN anime a ON a.id=latest.anime_id
 WHERE latest.verification_status='verified' AND a.identity_verification_status='identity_verified'
   AND latest.verified_at BETWEEN now()-interval '7 days' AND now();
COMMIT;
