-- Only run BEFORE migration_v0_2_1, on a disposable DB. Roll back every fixture.
-- A successful reproduction means v0.2 accepts invalid data, not that it is safe.
BEGIN;
DO $$
DECLARE aid bigint; bid bigint; sid bigint; bsid bigint; eid bigint; snapid bigint;
BEGIN
 INSERT INTO anime(title_ko) VALUES('__baseline_a__') RETURNING id INTO aid;
 INSERT INTO anime(title_ko) VALUES('__baseline_b__') RETURNING id INTO bid;
 INSERT INTO seasons(anime_id,canonical_season_number) VALUES(aid,1) RETURNING id INTO sid;
 INSERT INTO seasons(anime_id,canonical_season_number) VALUES(bid,1) RETURNING id INTO bsid;
 INSERT INTO episodes(season_id,canonical_episode_number) VALUES(bsid,1) RETURNING id INTO eid;
 INSERT INTO ott_platforms(name) VALUES('__baseline_platform__');
 INSERT INTO ott_upload_snapshots(anime_id,season_id,ott_platform) VALUES(aid,sid,'__baseline_platform__') RETURNING id INTO snapid;
 INSERT INTO ott_episode_mapping(snapshot_id,ott_episode_number,canonical_episode_id) VALUES(snapid,1,eid);
 IF NOT EXISTS(SELECT 1 FROM ott_episode_mapping WHERE snapshot_id=snapid AND canonical_episode_id=eid) THEN
   RAISE EXCEPTION 'baseline cross-anime gap not reproduced';
 END IF;
 INSERT INTO ott_upload_snapshots(anime_id,season_id,ott_platform,offer_type,availability_status,
   latest_episode_number,available_episode_count,available_episode_numbers,verification_status,
   source_url,verified_at,reviewer,source_method,evidence_reference,mapping_status)
 VALUES(aid,sid,'__baseline_platform__','subscription','available',1,1,ARRAY[1],'verified',
   'https://example.org/synthetic',now()+interval '1 day','fixture','licensed_feed','synthetic','verified');
 RAISE NOTICE 'REPRODUCED 2 baseline gaps: cross-anime mapping and future verified_at accepted';
END $$;
ROLLBACK;
