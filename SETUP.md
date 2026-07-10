# Publishing this portfolio with GitHub Pages

This repo generates `index.html` from your project cards. GitHub Pages serves
that file as a public webpage. Pick ONE option.

## Option A — Serve the committed page (simplest, recommended)
The skill rebuilds `index.html` locally and pushes it, so the page updates
whenever you catalog a project. No CI needed.

1. Push this repo to GitHub.
2. Repo **Settings → Pages**.
3. **Source: Deploy from a branch** → Branch: `main` → Folder: `/ (root)` → Save.
4. Wait ~1 min. Your site is at `https://USERNAME.github.io/REPO/`.
5. You can delete the `setup/` folder.

## Option B — Auto-rebuild on every push (incl. edits made on github.com)
Use this if you want to edit a card's JSON in the GitHub web UI and have the
page rebuild itself.

1. Move `setup/pages-workflow.yml.txt` to `.github/workflows/pages.yml`.
2. Repo **Settings → Pages → Source: GitHub Actions**.
3. Push. The Action runs `build.py` and deploys.

## Custom domain (optional)
Add a `CNAME` file containing your domain (e.g. `projects.yoursite.com`) and
point a DNS CNAME record at `USERNAME.github.io`. Then set the domain under
Settings → Pages.

## Editing the page's look
- Title / tagline / accent color / header links live in `site.json`.
- Deeper styling is the `<style>` block inside `build.py` (plain CSS).
- Never hand-edit `index.html` or `README.md` — they're regenerated.
