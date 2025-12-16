#!/bin/bash
#
# Script to push Unity wiki to GitHub
# Run this AFTER initializing the wiki on GitHub web interface
#

set -e

WIKI_DIR="/tmp/unity.wiki"
SOURCE_WIKI="/home/matthew/projects/HI/unity/wiki"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Unity GitHub Wiki Publisher                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Clone wiki repo
echo "📥 Cloning GitHub wiki repository..."
if [ -d "$WIKI_DIR" ]; then
    echo "   Removing existing wiki directory..."
    rm -rf "$WIKI_DIR"
fi

cd /tmp
git clone https://github.com/mylaniakea/unity.wiki.git

if [ ! -d "$WIKI_DIR" ]; then
    echo "❌ Failed to clone wiki repository."
    echo "   Make sure you've initialized the wiki on GitHub first!"
    echo "   Go to: https://github.com/mylaniakea/unity/wiki"
    echo "   Click 'Create the first page' and save it."
    exit 1
fi

# Step 2: Copy wiki files
echo "📝 Copying wiki content..."
cd "$WIKI_DIR"

cp "$SOURCE_WIKI/Home.md" . 2>/dev/null || echo "   Home.md not found"

# Copy other wiki files if they exist
for file in "$SOURCE_WIKI"/*.md; do
    if [ -f "$file" ] && [ "$(basename "$file")" != "Home.md" ]; then
        cp "$file" . 2>/dev/null || true
    fi
done

echo "   Copied $(ls -1 *.md 2>/dev/null | wc -l) markdown files"

# Step 3: Commit and push
echo "🔄 Committing changes..."
git add .

if git diff --staged --quiet; then
    echo "✅ No changes to commit (wiki is already up to date)"
else
    git commit -m "Update Unity wiki with Phase 4 integration complete

- Add Production Ready status
- Update with all 4 phases complete
- Add comprehensive statistics
- Include quick start guide
- Add production readiness dashboard

Version: 1.0.0-phase-4-complete
Date: $(date +%Y-%m-%d)"

    echo "📤 Pushing to GitHub..."
    git push origin master

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    ✅ Wiki Updated!                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "View at: https://github.com/mylaniakea/unity/wiki"
fi

# Cleanup
cd /home/matthew/projects/HI/unity
rm -rf "$WIKI_DIR"

echo ""
echo "Done! 🎉"
