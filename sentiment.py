from pathlib import Path

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

DATA_DIR = Path(__file__).parent / "data"


def score_comments():
    comments = pd.read_csv(DATA_DIR / "comments.csv")
    analyzer = SentimentIntensityAnalyzer()
    comments['compound'] = [analyzer.polarity_scores(str(t))['compound'] for t in comments['text']]
    return comments


def per_video(comments):
    g = comments.groupby('video_id')['compound']
    return pd.DataFrame({
        'n_comments': g.size(),
        'mean_sentiment': g.mean(),
        'share_positive': g.apply(lambda s: (s >= 0.05).mean()),
        'share_negative': g.apply(lambda s: (s <= -0.05).mean()),
    }).reset_index().rename(columns={'video_id': 'id'})


if __name__ == "__main__":
    scored = score_comments()
    per_video(scored).to_csv(DATA_DIR / "sentiment.csv", index=False)
