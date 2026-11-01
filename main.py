import os
import re
from datetime import datetime, timezone
from pathlib import Path

import googleapiclient.discovery
import googleapiclient.errors
import pandas as pd

PLAYLIST_ID = "PLAzrgbu8gEMIIK3r4Se1dOZWSZzUSadfZ"
DATA_DIR = Path(__file__).parent / "data"


def get_client():
    api_key = os.environ["YOUTUBE_API_KEY"]
    return googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)


def parse_duration(iso):
    """ISO 8601 duration (PT1H2M3S) -> seconds."""
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def extract_guests(title, description):
    """Guest names, '|'-joined. Titles start with the guest, so take the longest run of leading
    title words that appears verbatim in the description's opening, then split joint guests
    ("A and B"). Falls back to the first two title words when the description doesn't confirm any."""
    words = re.sub(r"\s*\|.*$", "", title).split()
    opening = re.sub(r"\s+", " ", description[:400])
    for k in range(min(len(words), 6), 0, -1):
        prefix = " ".join(words[:k])
        if prefix in opening and not re.search(r"\b(and|&)$", prefix):
            names = re.split(r"\s+(?:and|&)\s+|,\s*(?:and\s+)?", prefix)
            return "|".join(n.strip() for n in names if n.strip())
    return " ".join(words[:2])


def get_playlist_video_ids(youtube, playlist_id):
    ids, token = [], None
    while True:
        response = youtube.playlistItems().list(
            part="contentDetails", playlistId=playlist_id,
            maxResults=50, pageToken=token).execute()
        ids += [i['contentDetails']['videoId'] for i in response['items']]
        token = response.get('nextPageToken')
        if token is None:
            return ids


def get_video_details(youtube, video_ids):
    """Up to 50 ids per request, so ~10 calls instead of one per video."""
    rows = []
    for i in range(0, len(video_ids), 50):
        response = youtube.videos().list(
            part="contentDetails,statistics,snippet",
            id=",".join(video_ids[i:i + 50])).execute()
        for item in response['items']:
            stats = item['statistics']
            rows.append({
                'id': item['id'],
                'date': item['snippet']['publishedAt'],
                'title': item['snippet']['title'],
                'description': item['snippet'].get('description', ''),
                'guests': extract_guests(item['snippet']['title'], item['snippet'].get('description', '')),
                'duration_s': parse_duration(item['contentDetails']['duration']),
                'views': int(stats.get('viewCount', 0)),
                # likes/comments can be hidden or disabled -> NaN rather than dropping the video
                'likes': int(stats['likeCount']) if 'likeCount' in stats else None,
                'comments': int(stats['commentCount']) if 'commentCount' in stats else None,
                'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            })
    return rows


def get_top_comments(youtube, video_id, max_results=100):
    try:
        response = youtube.commentThreads().list(
            part="snippet", videoId=video_id, order="relevance",
            maxResults=max_results, textFormat="plainText").execute()
    except googleapiclient.errors.HttpError:
        return []  # comments disabled
    return [{'video_id': video_id,
             'text': c['snippet']['topLevelComment']['snippet']['textDisplay'],
             'likes': c['snippet']['topLevelComment']['snippet']['likeCount']}
            for c in response['items']]


def main(with_comments=True):
    DATA_DIR.mkdir(exist_ok=True)
    youtube = get_client()

    video_ids = get_playlist_video_ids(youtube, PLAYLIST_ID)
    details = pd.DataFrame(get_video_details(youtube, video_ids))
    details.to_csv(DATA_DIR / "videos.csv", index=False)

    # Append a dated snapshot so repeated runs build real growth curves.
    snapshots = DATA_DIR / "snapshots.csv"
    details[['id', 'fetched_at', 'views', 'likes', 'comments']].to_csv(
        snapshots, mode='a', header=not snapshots.exists(), index=False)

    if with_comments:
        comments = [c for vid in details['id'] for c in get_top_comments(youtube, vid)]
        pd.DataFrame(comments).to_csv(DATA_DIR / "comments.csv", index=False)


if __name__ == "__main__":
    main()
