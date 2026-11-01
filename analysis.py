from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = Path(__file__).parent / "data"


def load():
    # videos.csv has duration/comments; fall back to the original test.csv
    path = DATA_DIR / "videos.csv"
    if not path.exists():
        path = DATA_DIR / "test.csv"
    df = pd.read_csv(path)
    # guest interviews only: "wings" or "Holiday Extravaganza" (guest returns) in the title, not
    # host-led or compilation titles, 10+ minutes
    # (test.csv has no duration, so the length rule only applies when it's there)
    is_guest = (df['title'].str.contains('wings|Holiday Extravaganza', case=False)
                & ~df['title'].str.contains(r'^Sean Evans|Best |History|Compilation|Moments|Reactions', case=False))
    if 'duration_s' in df:
        is_guest &= df['duration_s'] >= 600
    df = df[is_guest].copy()
    df['date'] = pd.to_datetime(df['date'], utc=True)
    now = pd.Timestamp.now(tz='UTC')
    df['age_days'] = (now - df['date']).dt.days.clip(lower=1)
    df['views_per_day'] = df['views'] / df['age_days']
    df['like_rate'] = df['likes'] / df['views']
    df['title_len'] = df['title'].str.len()
    df['guest'] = df['title'].str.split(r' (?:While|Eats|Gets|Tries|Deeply|Puts|Savagely|Sauces)', n=1, regex=True).str[0]
    return df.sort_values('date').reset_index(drop=True)


def plot_views_over_time(df):
    fig, ax = plt.subplots(layout='constrained')
    ax.scatter(df['date'], df['views'], s=12)
    ax.set_yscale('log')
    ax.set_title('Views by publish date')
    return fig


def plot_views_per_day(df):
    fig, ax = plt.subplots(layout='constrained')
    ax.scatter(df['date'], df['views_per_day'], s=12)
    ax.set_yscale('log')
    ax.set_title('Views per day since upload')
    return fig


def overperformers(df, n=15):
    """Rank by views/day and like rate, plus a residual vs. the trend of views/day over time."""
    d = df.copy()
    d['trend'] = d['views_per_day'].rolling(30, center=True, min_periods=5).median()
    d['vs_trend'] = d['views_per_day'] / d['trend']
    return (d.sort_values('vs_trend', ascending=False)
             [['title', 'views', 'views_per_day', 'like_rate', 'vs_trend']].head(n))


def title_word_effect(df, min_count=5):
    words = df.assign(word=df['title'].str.lower().str.findall(r"[a-z']+")).explode('word')
    g = words.groupby('word').agg(n=('id', 'nunique'), median_vpd=('views_per_day', 'median'))
    return g[g['n'] >= min_count].sort_values('median_vpd', ascending=False)


if __name__ == "__main__":
    df = load()
    df['minutes'] = df['duration_s'] / 60
    df['comments_per_k'] = df['comments'] / df['views'] * 1000
    print(len(df), 'guest interviews')
    # Spearman = Pearson on ranks (corrwith(method='spearman') needs scipy)
    print(df[['title_len', 'minutes', 'like_rate', 'comments_per_k']].rank().corrwith(df['views_per_day'].rank()))
    print(overperformers(df).to_string())
    print(title_word_effect(df).head(20))
    plot_views_over_time(df)
    plot_views_per_day(df)
    plt.show()
