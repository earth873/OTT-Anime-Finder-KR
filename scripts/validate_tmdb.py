#!/usr/bin/env python3
"""TMDB read-only evaluation for Korean anime OTT catalog matching.
Noncommercial evaluation only; review TMDB terms before any public/commercial launch.
"""
import argparse,csv,json,math,os,sys,time,urllib.request,urllib.parse,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HEADERS=['query','tmdb_id','matched_title','original_name','first_air_date','match_status','match_candidates','providers_kr_subscription','providers_kr_rent','providers_kr_buy','season_count','official_episode_count','production_status','tmdb_url','provider_source_url','checked_at_utc','provider_scope','ott_latest_episode','ott_episode_verification']
TARGETS=[('진격의 거인','Attack on Titan'),('귀멸의 칼날','Demon Slayer: Kimetsu no Yaiba'),('주술회전','Jujutsu Kaisen'),('스파이 패밀리','SPY x FAMILY'),('장송의 프리렌','Frieren: Beyond Journey’s End'),('나 혼자만 레벨업','Solo Leveling'),('최애의 아이','Oshi no Ko'),('약사의 혼잣말','The Apothecary Diaries'),('체인소 맨','Chainsaw Man'),('원피스','One Piece'),('나루토','Naruto'),('블리치','Bleach'),('하이큐!!','Haikyu!!'),('강철의 연금술사 BROTHERHOOD','Fullmetal Alchemist: Brotherhood'),('헌터×헌터','Hunter x Hunter'),('데스노트','Death Note'),('코드 기아스','Code Geass'),('슈타인즈 게이트','Steins;Gate'),('소드 아트 온라인','Sword Art Online'),('전생했더니 슬라임이었던 건에 대하여','That Time I Got Reincarnated as a Slime'),('리제로','Re:ZERO -Starting Life in Another World-'),('무직전생','Mushoku Tensei: Jobless Reincarnation'),('던전밥','Delicious in Dungeon'),('사이버펑크 엣지러너','Cyberpunk: Edgerunners'),('바이올렛 에버가든','Violet Evergarden'),('4월은 너의 거짓말','Your Lie in April'),('봇치 더 록!','Bocchi the Rock!'),('케이온!','K-On!'),('코노스바','KonoSuba'),('메이드 인 어비스','Made in Abyss')]

def get(path,params,token):
    url='https://api.themoviedb.org/3'+path+'?'+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'Accept':'application/json','User-Agent':'OTTAnimeEvaluation/0.1'})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=20) as resp: return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code not in (429,500,502,503,504) or attempt==3: raise
            try:delay=float((e.headers or {}).get('Retry-After') or 2**attempt)
            except (TypeError,ValueError):delay=2**attempt
            if not math.isfinite(delay) or delay < 0:delay=2**attempt
        except (TimeoutError,urllib.error.URLError):
            if attempt==3: raise
            delay=2**attempt
        time.sleep(min(delay,30))

def choose(results,english):
    from matching import choose_candidate
    candidate,status,_=choose_candidate(results,None,[english])
    return candidate,status,len(results)

def main():
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=30);p.add_argument('--delay',type=float,default=.3);p.add_argument('--output',default=str(ROOT/'data'/'tmdb_results.csv'));args=p.parse_args()
    if Path(args.output).resolve() == (ROOT/'data'/'tmdb_results.csv').resolve() and (ROOT/'data'/'tmdb_results.csv').exists():
        p.error('Existing baseline cannot be overwritten; use --output with a new path.')
    token=os.environ.get('TMDB_READ_ACCESS_TOKEN','').strip()
    if not token:sys.exit('TMDB_READ_ACCESS_TOKEN 환경변수를 설정해 주세요. 결과는 생성되지 않았습니다.')
    from datetime import datetime,timezone
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,HEADERS);writer.writeheader()
        for i,(ko,en) in enumerate(TARGETS[:max(0,min(args.limit,len(TARGETS)))],1):
            row=dict.fromkeys(HEADERS,'')
            row.update(query=ko,provider_scope='TV_SERIES_KR_NOT_EPISODE',ott_episode_verification='NOT_CHECKED')
            try:
                found=get('/search/tv',{'query':en,'language':'en-US','include_adult':'false'},token)
                candidate,status,count=choose(found.get('results',[]),en)
                row['match_status']=status;row['match_candidates']=count
                if candidate:
                    cid=candidate['id'];row['tmdb_id']=cid;row['tmdb_url']=f'https://www.themoviedb.org/tv/{cid}'
                    details=get(f'/tv/{cid}',{'language':'ko-KR'},token)
                    providers=get(f'/tv/{cid}/watch/providers',{},token).get('results',{}).get('KR',{})
                    row.update(matched_title=details.get('name',''),original_name=details.get('original_name',''),first_air_date=details.get('first_air_date',''),production_status=details.get('status',''),season_count=details.get('number_of_seasons',''),official_episode_count=details.get('number_of_episodes',''),provider_source_url=providers.get('link',''))
                    for field,source in [('providers_kr_subscription','flatrate'),('providers_kr_rent','rent'),('providers_kr_buy','buy')]:
                        row[field]=' | '.join(sorted({p.get('provider_name','') for p in providers.get(source,[]) if p.get('provider_name')}))
                row['checked_at_utc']=datetime.now(timezone.utc).isoformat()
            except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError) as e:row['match_status']=f'error:{type(e).__name__}'
            writer.writerow(row);f.flush();print(f'[{i}/{min(args.limit,len(TARGETS))}] {ko}: {row["match_status"]}')
            time.sleep(max(0,args.delay))
    print(f'완료: {out} (자동 매칭 결과는 수동 검토 필요; 실제 OTT별 회차는 미확인)')
if __name__=='__main__':main()
