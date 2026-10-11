-- PostgreSQL integration assertions. Synthetic fixtures only, all rolled back.
BEGIN;
CREATE TEMP TABLE assertions(label text PRIMARY KEY);
CREATE FUNCTION pg_temp.assert_true(condition boolean,label text) RETURNS void LANGUAGE plpgsql AS $$
BEGIN
 IF condition IS DISTINCT FROM true THEN RAISE EXCEPTION 'assertion failed: %',label; END IF;
 INSERT INTO assertions VALUES(label);
END $$;
CREATE FUNCTION pg_temp.expect_rejected(statement text,expected_state text,label text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE actual_state text;
BEGIN
 BEGIN
   EXECUTE statement;
 EXCEPTION WHEN OTHERS THEN
   GET STACKED DIAGNOSTICS actual_state=RETURNED_SQLSTATE;
   IF actual_state<>expected_state THEN RAISE EXCEPTION 'unexpected SQLSTATE % for %',actual_state,label; END IF;
   INSERT INTO assertions VALUES(label);
   RETURN;
 END;
 RAISE EXCEPTION 'invalid data accepted: %',label;
END $$;

DO $$
DECLARE aid bigint; bid bigint; sid bigint; sid2 bigint; bsid bigint;
 eid bigint; eid2 bigint; beid bigint; snapid bigint; other_snap bigint; unknown_snap bigint;
BEGIN
 INSERT INTO anime(title_ko,identity_verification_status) VALUES('__phase21_a__','identity_verified') RETURNING id INTO aid;
 INSERT INTO anime(title_ko) VALUES('__phase21_b__') RETURNING id INTO bid;
 INSERT INTO seasons(anime_id,canonical_season_number) VALUES(aid,1) RETURNING id INTO sid;
 INSERT INTO seasons(anime_id,canonical_season_number) VALUES(aid,2) RETURNING id INTO sid2;
 INSERT INTO seasons(anime_id,canonical_season_number) VALUES(bid,1) RETURNING id INTO bsid;
 INSERT INTO episodes(season_id,canonical_episode_number) VALUES(sid,1) RETURNING id INTO eid;
 INSERT INTO episodes(season_id,canonical_episode_number) VALUES(sid2,1) RETURNING id INTO eid2;
 INSERT INTO episodes(season_id,canonical_episode_number) VALUES(bsid,1) RETURNING id INTO beid;
 INSERT INTO ott_platforms(name) VALUES('__phase21_platform_a__'),('__phase21_platform_b__');
 INSERT INTO ott_upload_snapshots(anime_id,season_id,ott_platform) VALUES(aid,sid,'__phase21_platform_a__') RETURNING id INTO unknown_snap;
 PERFORM pg_temp.assert_true((SELECT latest_episode_number IS NULL AND available_episode_count IS NULL
   AND available_episode_numbers IS NULL FROM ott_upload_snapshots WHERE id=unknown_snap),'unknown episodes are NULL');
 PERFORM pg_temp.expect_rejected(format('UPDATE ott_upload_snapshots SET available_episode_count=0 WHERE id=%s',unknown_snap),'23514','unknown cannot imply zero');
 PERFORM pg_temp.expect_rejected(format('UPDATE ott_upload_snapshots SET anime_id=%s WHERE id=%s',bid,unknown_snap),'23503','snapshot anime-season FK');

 INSERT INTO ott_upload_snapshots(anime_id,season_id,ott_platform,offer_type,availability_status,
   latest_episode_number,available_episode_count,available_episode_numbers,verification_status,
   source_url,verified_at,reviewer,source_method,evidence_reference,mapping_status)
 VALUES(aid,sid,'__phase21_platform_a__','subscription','available',12,3,ARRAY[1,3,12],'verified',
   'https://example.org/synthetic',now(),'fixture','licensed_feed','synthetic','verified') RETURNING id INTO snapid;
 INSERT INTO ott_upload_snapshots(anime_id,season_id,ott_platform,offer_type,availability_status,
   latest_episode_number,available_episode_count,available_episode_numbers,verification_status,
   source_url,verified_at,reviewer,source_method,evidence_reference,mapping_status)
 VALUES(aid,sid,'__phase21_platform_b__','subscription','available',3,2,ARRAY[1,3],'verified',
   'https://example.org/synthetic',now(),'fixture','licensed_feed','synthetic','verified') RETURNING id INTO other_snap;
 PERFORM pg_temp.assert_true((SELECT latest_episode_number=12 AND available_episode_count=3 FROM ott_upload_snapshots WHERE id=snapid),'gapped episode max differs from count');
 PERFORM pg_temp.assert_true((SELECT count(*)=2 FROM latest_verified_ott_uploads WHERE anime_id=aid),'different OTT upload counts coexist');
 PERFORM pg_temp.assert_true((SELECT count(*)=2 FROM episodes e JOIN seasons s ON s.id=e.season_id WHERE s.anime_id=aid),'official episodes not filled from OTT numbers');
 PERFORM pg_temp.expect_rejected(format('UPDATE ott_upload_snapshots SET available_episode_numbers=ARRAY[1,1,12] WHERE id=%s',snapid),'23514','duplicate upload numbers');
 PERFORM pg_temp.expect_rejected(format('UPDATE ott_upload_snapshots SET available_episode_count=12 WHERE id=%s',snapid),'23514','count is list length');
 PERFORM pg_temp.expect_rejected(format('UPDATE ott_upload_snapshots SET latest_episode_number=3 WHERE id=%s',snapid),'23514','latest is list maximum');
 PERFORM pg_temp.expect_rejected(format('UPDATE ott_upload_snapshots SET available_episode_numbers=NULL WHERE id=%s',snapid),'23514','verified list cannot be NULL');
 PERFORM pg_temp.expect_rejected(format('UPDATE ott_upload_snapshots SET verified_at=now()+interval ''1 day'' WHERE id=%s',snapid),'23514','future verified time blocked');
 PERFORM pg_temp.expect_rejected(format('UPDATE ott_upload_snapshots SET mapping_status=''review_required'' WHERE id=%s',snapid),'23514','unreviewed season mapping cannot publish');

 PERFORM pg_temp.expect_rejected(format('INSERT INTO ott_episode_mapping(snapshot_id,ott_episode_number,canonical_episode_id) VALUES(%s,1,%s)',snapid,beid),'23514','cross-anime mapping blocked');
 INSERT INTO ott_episode_mapping(snapshot_id,ott_episode_number,canonical_episode_id,verification_status,source_url,verified_at)
 VALUES(snapid,1,eid,'verified','https://example.org/synthetic',now()),(snapid,3,eid2,'verified','https://example.org/synthetic',now());
 PERFORM pg_temp.assert_true((SELECT count(*)=2 FROM ott_episode_mapping WHERE snapshot_id=snapid),'same anime cross-season part mapping allowed');
 PERFORM pg_temp.expect_rejected(format('INSERT INTO ott_episode_mapping(snapshot_id,ott_episode_number,canonical_episode_id,verification_status,source_url,verified_at) VALUES(%s,2,%s,''verified'',''https://example.org/synthetic'',now())',snapid,eid),'23514','unobserved OTT episode mapping blocked');
 PERFORM pg_temp.expect_rejected(format('INSERT INTO ott_episode_mapping(snapshot_id,ott_episode_number,canonical_episode_id) VALUES(%s,1,%s)',snapid,eid),'23505','duplicate mapping blocked');
 PERFORM pg_temp.expect_rejected(format('UPDATE episodes SET season_id=%s WHERE id=%s',bsid,eid),'23514','mapped episode parent update blocked');
 PERFORM pg_temp.expect_rejected(format('UPDATE seasons SET anime_id=%s WHERE id=%s',bid,sid2),'23514','mapped season identity update blocked');
 PERFORM pg_temp.expect_rejected(format('UPDATE ott_upload_snapshots SET available_episode_numbers=ARRAY[3,12],available_episode_count=2 WHERE id=%s',snapid),'23514','snapshot cannot remove mapped observed episode');

 UPDATE ott_upload_snapshots SET verified_at=now()-interval '8 days' WHERE id=other_snap;
 PERFORM pg_temp.assert_true((SELECT count(*)=0 FROM latest_verified_ott_uploads WHERE id=other_snap),'old verification hidden');
 UPDATE anime SET identity_verification_status='review_required' WHERE id=aid;
 PERFORM pg_temp.assert_true((SELECT count(*)=0 FROM latest_verified_ott_uploads WHERE anime_id=aid),'unverified identity hidden');
 UPDATE anime SET identity_verification_status='identity_verified' WHERE id=aid;
 INSERT INTO ott_upload_snapshots(anime_id,season_id,ott_platform,offer_type)
 VALUES(aid,sid,'__phase21_platform_a__','subscription');
 PERFORM pg_temp.assert_true((SELECT count(*)=0 FROM latest_verified_ott_uploads WHERE id=snapid),'new unknown observation hides old verified');
END $$;
SELECT count(*) AS passed_assertions FROM assertions;
SELECT label FROM assertions ORDER BY label;
ROLLBACK;
