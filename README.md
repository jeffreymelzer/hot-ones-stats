# Hot Ones stats

Collects stats for every video in a YouTube playlist (currently the Hot Ones playlist) and looks at
what drives views: publish date, video length, guest, title wording, and comment sentiment.

## Setup

```
pip install -r requirements.txt
```

Create a YouTube Data API v3 key in Google Cloud Console and put it in an environment variable
(never in the code):

```powershell
$env:YOUTUBE_API_KEY = "your-key"
```

## Run

| Script | What it does |
|---|---|
| `main.py` | Fetches the playlist: views, likes, comments, duration, description, guest names and the top 100 comments per video. Writes `data/videos.csv`, `data/comments.csv` and appends a dated row per video to `data/snapshots.csv` (run it on a schedule to build growth curves). |
| `sentiment.py` | Scores the top comments with VADER and writes `data/sentiment.csv`, one row per video. |
| `build_site.py` | Builds `docs/data.json` (per-video stats and sentiment only, no comments or descriptions) for the GitHub Pages site in `docs/`. Re-run it after `main.py` and `sentiment.py` to refresh the page. |
| `analysis.py` | Guest interviews only: views per day, correlations with views per day, title-word effects, overperformers, plots. |

Guest names come from each video description: the longest run of leading title words that also appears
in the description. Guest interviews are titles containing "wings" or "Holiday Extravaganza" that are
at least 10 minutes long and not host-led or compilation videos.

## Site

`docs/index.html` is a static page (d3 from a CDN, data from `docs/data.json`). Serve it locally with
`python -m http.server --directory docs`, or publish it with GitHub Pages: Settings → Pages, branch
`main`, folder `/docs`.

The `data/` folder is not tracked. Re-create it by running the scripts above.
