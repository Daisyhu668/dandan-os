#!/usr/bin/env bash
set -euo pipefail
# Run from project root, AFTER an empty Private GitHub repository is created and authenticated.
# No credentials belong in this script.
REPO="https://github.com/Daisyhu668/dandan-os.git"
if [ -d .git ]; then echo 'Existing Git repository: inspect before changing remote'; exit 1; fi
if [ ! -f package.json ] || [ ! -f wrangler.jsonc ]; then echo 'Please run in project root'; exit 1; fi
git init -b main
git add .
git status --short
git commit -m "feat: Dandan OS 3.0 Cloudflare portfolio and photo gallery"
git remote add origin "$REPO"
echo "Ready to push. First verify remote exists and is the intended private repository. Then run: git push -u origin main"
