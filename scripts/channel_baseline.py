"""채널 기준선 측정 — survey/08-measurement-baseline.md 의 판정에 쓴다.

실행: venv/bin/python3 scripts/channel_baseline.py
결과: survey/baseline-<날짜>.json
"""
import sys, json, datetime
sys.path.insert(0, '/home/mh/ocstorage/workspace/nichproject')
from auto_publisher.video_uploader import _load_credentials
from googleapiclient.discovery import build

yt = build("youtube", "v3", credentials=_load_credentials())
ch = yt.channels().list(part="statistics,contentDetails", mine=True).execute()["items"][0]
st = ch["statistics"]
subs, views, vids = int(st["subscriberCount"]), int(st["viewCount"]), int(st["videoCount"])

# 업로드 재생목록에서 쇼츠/롱폼 분리
up = ch["contentDetails"]["relatedPlaylists"]["uploads"]
ids, tok = [], None
while True:
    r = yt.playlistItems().list(part="contentDetails", playlistId=up, maxResults=50, pageToken=tok).execute()
    ids += [i["contentDetails"]["videoId"] for i in r["items"]]
    tok = r.get("nextPageToken")
    if not tok: break

shorts_v = long_v = 0; shorts_n = long_n = 0
for i in range(0, len(ids), 50):
    r = yt.videos().list(part="statistics,snippet", id=",".join(ids[i:i+50])).execute()
    for it in r["items"]:
        v = int(it["statistics"].get("viewCount", 0))
        if "#shorts" in it["snippet"]["title"].lower():
            shorts_v += v; shorts_n += 1
        else:
            long_v += v; long_n += 1

out = {
    "date": datetime.date.today().isoformat(),
    "subscribers": subs, "total_views": views, "total_videos": vids,
    "shorts": {"count": shorts_n, "views": shorts_v,
               "per_video": round(shorts_v / shorts_n, 1) if shorts_n else 0},
    "longform": {"count": long_n, "views": long_v,
                 "per_video": round(long_v / long_n, 1) if long_n else 0},
    "subs_per_1k_views": round(subs / (views / 1000), 3) if views else 0,
}
print(json.dumps(out, ensure_ascii=False, indent=2))
open(f"/home/mh/ocstorage/workspace/nichproject/survey/baseline-{out['date']}.json", "w").write(
    json.dumps(out, ensure_ascii=False, indent=2))
