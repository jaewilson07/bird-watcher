# Tutorials

One Colab-compatible Jupyter notebook per issue.

## How to open in Google Colab

Click the badge at the top of any notebook, or:

1. Go to https://colab.research.google.com/
2. Click **File → Open notebook → GitHub**
3. Search for `jaewilson07/bird-watcher`
4. Pick the notebook you want

## Order

Work through them in order — each one builds on the last.

| # | Notebook | Issue |
|---|---|---|
| 1 | [01-setup.ipynb](01-setup.ipynb) | [Step 1: Setup the project](../issues/1) |
| 2 | [02-stream.ipynb](02-stream.ipynb) | [Step 2: View the stream](../issues/2) |
| 3 | [03-poll.ipynb](03-poll.ipynb) | [Step 3: Poll every N seconds](../issues/3) |
| 4 | [04-detect.ipynb](04-detect.ipynb) | [Step 4: Detect (yes/no)](../issues/4) |
| 5 | [05-identify.ipynb](05-identify.ipynb) | [Step 5: Identify species](../issues/5) |
| 6 | [06-persist.ipynb](06-persist.ipynb) | [Step 6: Persist sightings](../issues/6) |
| 7 | [07-slack.ipynb](07-slack.ipynb) | [Step 7: Slack notifications](../issues/7) |
| 8 | [08-web-hello.ipynb](08-web-hello.ipynb) | [Step 8: Web UI hello world](../issues/8) |
| 9 | [09-gallery.ipynb](09-gallery.ipynb) | [Step 9: Web UI gallery](../issues/9) |
| 10 | [10-digest.ipynb](10-digest.ipynb) | [Step 10: Daily digest](../issues/10) |

Each notebook has:
- Markdown narrative explaining what's happening
- Code cells you can run one at a time
- An acceptance criterion at the end (a visible result)
- A "what's next" preview pointing to the next issue

All notebooks work in Colab (with a sample bird image fallback when your phone isn't reachable). They also work locally on your laptop — just `pip install -r requirements.txt` and `jupyter lab`.