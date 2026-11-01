"""Build docs/data.json for the GitHub Pages site from data/videos.csv and data/sentiment.csv.

Only per-video stats go into the page: no comments and no descriptions.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
DOCS_DIR = ROOT / "docs"


def build():
    videos = pd.read_csv(ROOT / "data" / "videos.csv")
    sentiment = pd.read_csv(ROOT / "data" / "sentiment.csv")[['id', 'mean_sentiment']]
    df = videos.merge(sentiment, on='id', how='left')

    # same guest-interview rule as analysis.py
    guest = (df['title'].str.contains('wings|Holiday Extravaganza', case=False)
             & ~df['title'].str.contains(r'^Sean Evans|Best |History|Compilation|Moments|Reactions', case=False)
             & (df['duration_s'] >= 600))
    df = df[guest].copy()

    now = pd.Timestamp.now(tz='UTC')
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df['age_days'] = (now - df['date']).dt.days.clip(lower=1)
    df['vpd'] = df['views'] / df['age_days']
    df = df.sort_values('date').reset_index(drop=True)
    # pace against the median of the 30 episodes around it
    df['trend'] = df['vpd'].rolling(31, center=True, min_periods=1).median()
    df['vs_trend'] = df['vpd'] / df['trend']

    episodes = pd.DataFrame({
        'id': df['id'],
        'title': df['title'].str.replace(r' \| Hot Ones.*$', '', regex=True),
        'date': df['date'].dt.strftime('%Y-%m-%d'),
        'views': df['views'],
        'likes': df['likes'],
        'minutes': (df['duration_s'] / 60).round(1),
        'comments_per_k': (df['comments'] / df['views'] * 1000).round(2),
        'vpd': df['vpd'].round(1),
        'vs_trend': df['vs_trend'].round(3),
        'sentiment': df['mean_sentiment'].round(3),
        'guests': df['guests'],
    })
    DOCS_DIR.mkdir(exist_ok=True)
    out = {'built': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
           'episodes': json.loads(episodes.to_json(orient='records'))}
    (DOCS_DIR / "data.json").write_text(json.dumps(out, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
    return len(episodes)


if __name__ == "__main__":
    print(build(), "episodes written to docs/data.json")
