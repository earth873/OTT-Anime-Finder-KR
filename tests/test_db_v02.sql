-- Run against a disposable PostgreSQL database AFTER schema.sql and migration_v0_2.sql.
-- All fixtures are rolled back. These are synthetic tests, not real availability data.
BEGIN;
DO $$
DECLARE aid bigint; sid bigint; other_aid bigint;
BEGIN
 INSERT INTO anime(title_ko,identity_verification_status) VALUES('__v02_test__','identity_verified') RETURNING id INTO aid;
 INSERT INTO anime(title_ko) VALUES('__v02_other__') RETURNING id INTO other_aid;
 INSERT INTO seasons(anime_id,canonical_season_number) VALUES(aid,1) RETURNING id INTO sid;
 INSERT INTO ott_platforms(name) VALUES('__v02_test_platform__');
 INSERT INTO ott_upload_snapshots(anime_id,season_id,ott_platform,
    offer_type,availability_status,latest_episode_number,available_episode_count,
    available_episode_numbers,verification_status,source_url,verified_at,reviewer,
    source_method,evidence_reference,mapping_status)
 VALUES(aid,sid,'__v02_test_platform__','subscription','available',12,3,ARRAY[1,3,12],
    'verified','https://example.org/test-fixture',now(),'fixture','licensed_feed','fixture','verified');
 IF NOT EXISTS(SELECT 1 FROM latest_verified_ott_uploads WHERE anime_id=aid) THEN
   RAISE EXCEPTION 'verified current observation hidden';
 END IF;
 BEGIN
   INSERT INTO ott_upload_snapshots(anime_id,season_id,ott_platform,available_episode_count)
     VALUES(aid,sid,'__v02_test_platform__',12);
   RAISE EXCEPTION 'unverified numbers accepted';
 EXCEPTION WHEN check_violation THEN NULL;
 END;
 BEGIN
   INSERT INTO ott_upload_snapshots(anime_id,season_id,ott_platform)
     VALUES(other_aid,sid,'__v02_test_platform__');
   RAISE EXCEPTION 'cross-anime season accepted';
 EXCEPTION WHEN foreign_key_violation THEN NULL;
 END;
 IF valid_ott_episode_numbers(ARRAY[1,1]) OR valid_ott_episode_numbers(ARRAY[3,1])
    OR valid_ott_episode_numbers(ARRAY[0]) OR valid_ott_episode_numbers(ARRAY[NULL::integer]) THEN
   RAISE EXCEPTION 'bad episode list accepted';
 END IF;
 INSERT INTO ott_upload_snapshots(anime_id,season_id,ott_platform,offer_type)
   VALUES(aid,sid,'__v02_test_platform__','subscription');
 IF EXISTS(SELECT 1 FROM latest_verified_ott_uploads WHERE anime_id=aid) THEN
   RAISE EXCEPTION 'old observation leaked after later unverified observation';
 END IF;
END $$;
ROLLBACK;
