# GitHub Pages Setup Guide

## 🌐 Hosting Your Unity Plugin Showcase

The beautiful plugin showcase HTML is ready to be hosted on GitHub Pages!

### Quick Setup

1. **Go to your GitHub repository**: https://github.com/mylaniakea/unity

2. **Navigate to Settings**:
   - Click the "Settings" tab at the top of the repo

3. **Enable GitHub Pages**:
   - Scroll down to the "Pages" section in the left sidebar
   - Under "Build and deployment":
     - **Source**: Select "Deploy from a branch"
     - **Branch**: Select "main" 
     - **Folder**: Select "/ (root)"
   - Click "Save"

4. **Wait for deployment** (usually 1-2 minutes)

5. **Access your showcase**:
   - Your site will be live at: **https://mylaniakea.github.io/unity/**
   - The root `index.html` will redirect to `docs/unity_plugins_showcase.html`

### What You'll See

A stunning, interactive showcase of all 40 Unity plugins with:
- ✨ Beautiful gradient background
- 📱 Responsive design (mobile-friendly)
- 🎨 Color-coded plugin cards by category
- 🏷️ Tag system for easy filtering
- 🎭 Smooth animations and hover effects
- 📊 Live statistics (40 plugins, 3 tiers, 7 categories)
- 🎯 Organized by tier (Essential, Quality of Life, Power User, Foundation)

### File Structure

```
unity/
├── index.html                           # Root redirect page
└── docs/
    └── unity_plugins_showcase.html     # Main showcase page
```

### Custom Domain (Optional)

If you want to use a custom domain:
1. Add a `CNAME` file in the root with your domain
2. Configure DNS records at your domain provider
3. Enable "Enforce HTTPS" in GitHub Pages settings

### Updating the Showcase

Any time you add new plugins:
1. Update `docs/unity_plugins_showcase.html`
2. Commit and push to main
3. GitHub Pages will auto-deploy in ~1-2 minutes

### Share It!

Once live, share your beautiful plugin showcase:
- Add the link to your README
- Share in homelab communities
- Show off your 40-plugin monitoring platform!

---

**Note**: The site is static HTML/CSS/JS - no build process needed. GitHub serves it directly!

*Co-Authored-By: Warp <agent@warp.dev>*
