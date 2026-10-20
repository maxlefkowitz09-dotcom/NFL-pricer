# NFL Game-Winner Pricer

A self-updating website. Every 10 minutes a GitHub Action pulls the NFL schedule and scores (ESPN) and
game-winner odds (Polymarket), saves them, and republishes the site. The site prices a hypothetical option
on each favorite's margin of victory, locks the pregame price at kickoff, and tracks whether selling those
options would have made money as games finish.

## Setup (about 5 minutes, no coding)
1. On github.com, click **New repository**, name it (for example `nfl-pricer`), choose **Public**, and create it.
2. Upload the files: **Add file → Upload files**, drag in the `docs` and `scripts` folders and `README.md`, then commit.
3. Add the workflow: **Add file → Create new file**. In the name box type `.github/workflows/update.yml`
   (typing the slashes creates the folders), paste in the contents of that file from this project, and commit.
   (This is done by hand because browsers often skip folders that start with a dot.)
4. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
5. **Settings → Actions → General → Workflow permissions → Read and write permissions**, then Save.
6. Open the **Actions** tab, click **Update NFL data and deploy site → Run workflow**. After about a minute your
   site is live at `https://YOUR-USERNAME.github.io/REPO-NAME/` (also shown in the run's summary).

## Notes
- Updates run about every 10 minutes; GitHub can delay scheduled runs, so it's near-real-time, not instant.
- Odds are saved until kickoff, then locked. Games that started before you set this up have no saved pregame odds.
- If Polymarket has no matching market for a game, the site falls back to ESPN's odds and labels the source.
- GitHub pauses scheduled workflows in a repo with no activity for 60 days; re-enable under the Actions tab if needed.
- The Polymarket matching in `scripts/update.py` was written without live access, so check the first run's log
  (Actions tab). If every game says "ESPN odds", the Polymarket matching needs a tweak.
