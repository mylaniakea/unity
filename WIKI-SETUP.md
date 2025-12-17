# GitHub Wiki Setup Guide

This guide explains how to push the Unity wiki documentation to your GitHub repository's wiki.

## Wiki Pages Created

We've created the following comprehensive wiki pages:

1. **Home.md** - Main wiki landing page with project overview
2. **Quick-Start-Guide.md** - Get Unity running in under 10 minutes
3. **Integration-Overview.md** - Complete integration strategy and phases

## Pushing Wiki to GitHub

GitHub wikis are actually Git repositories. Here's how to set up and push the wiki:

### Option 1: Using GitHub Web Interface (Easiest)

1. Go to your repository: https://github.com/mylaniakea/unity
2. Click the **"Wiki"** tab
3. Click **"Create the first page"**
4. For each wiki page:
   - Click **"New Page"**
   - Copy content from `wiki/[PageName].md`
   - Paste into the editor
   - Click **"Save Page"**

### Option 2: Using Git (Recommended for Bulk Upload)

GitHub wikis are Git repositories with a special URL pattern.

#### Step 1: Clone the Wiki Repository

```bash
cd /home/matthew/projects/HI/unity
git clone https://github.com/mylaniakea/unity.wiki.git wiki-repo
```

#### Step 2: Copy Wiki Pages

```bash
cp wiki/*.md wiki-repo/
cd wiki-repo
```

#### Step 3: Push to GitHub

```bash
git add *.md
git commit -m "Add comprehensive Unity wiki documentation

- Home page with project overview
- Quick Start Guide
- Integration Overview
- Architecture documentation
- API reference

Created: December 15, 2024"

git push origin master
```

### Option 3: Initialize Wiki if It Doesn't Exist

If the wiki hasn't been created yet:

1. Go to https://github.com/mylaniakea/unity/wiki
2. Click **"Create the first page"**
3. Add any content and click **"Save Page"**
4. Now the wiki Git repository exists
5. Follow **Option 2** above to push the rest of the pages

## Wiki Structure

```
unity.wiki/
├── Home.md                        # Main landing page
├── Quick-Start-Guide.md           # Getting started
├── Integration-Overview.md        # Integration strategy
└── [Future pages to add]
    ├── Architecture-Overview.md
    ├── API-Overview.md
    ├── Credential-Management.md
    ├── Infrastructure-Monitoring.md
    ├── Container-Automation.md
    ├── Development-Setup.md
    ├── Deployment-Guide.md
    └── Troubleshooting.md
```

## Accessing the Wiki

Once pushed, your wiki will be available at:
https://github.com/mylaniakea/unity/wiki

## Wiki Navigation

GitHub wiki pages use double-bracket notation for internal links:
- `[[Page Name]]` - Link to a wiki page
- `[[Page Name|Display Text]]` - Link with custom text

Example:
```markdown
See the [[Quick Start Guide]] for installation instructions.
Or: [[Quick Start Guide|click here to get started]].
```

## Adding More Pages

To add more wiki pages later:

1. Clone the wiki repo: `git clone https://github.com/mylaniakea/unity.wiki.git`
2. Create new `.md` files
3. Commit and push: `git add . && git commit -m "Add new page" && git push`

Or use the GitHub web interface to create pages directly.

## Wiki Page Template

Use this template for new wiki pages:

```markdown
# Page Title

Brief introduction to what this page covers.

## Section 1

Content here...

## Section 2

More content...

## Further Reading

- [[Related Page 1]]
- [[Related Page 2]]

---

**See Also**: [[Home]] | [[Quick Start Guide]]
```

## Recommended Pages to Add Next

Once you've pushed the initial wiki, consider adding these pages:

### Technical Documentation
- **Architecture-Overview.md** - System architecture diagrams
- **Database-Schema.md** - Complete database schema
- **API-Overview.md** - API endpoints reference
- **Service-Layer-Architecture.md** - Service patterns

### Feature Documentation
- **Credential-Management.md** - KC-Booth features
- **Infrastructure-Monitoring.md** - BD-Store features
- **Container-Automation.md** - Uptainer features
- **Plugin-System.md** - Plugin architecture
- **Alert-System.md** - Alert and notification system
- **AI-Integration.md** - AI-powered features

### Development
- **Development-Setup.md** - Local development environment
- **Adding-New-Features.md** - Feature development guide
- **Testing-Guide.md** - Testing strategies
- **Contributing.md** - Contribution guidelines
- **Code-Style.md** - Code conventions

### Operations
- **Deployment-Guide.md** - Production deployment
- **Docker-Deployment.md** - Docker/Compose setup
- **Kubernetes-Deployment.md** - K8s deployment
- **Configuration-Reference.md** - All config options
- **Environment-Variables.md** - Environment variable reference
- **Monitoring-and-Observability.md** - Metrics and logging
- **Backup-and-Recovery.md** - Data protection
- **Troubleshooting.md** - Common issues and solutions
- **Security-Best-Practices.md** - Security guidelines

### Integration
- **Phase-1-2-KC-Booth-Integration.md** - KC-Booth integration details
- **Phase-3-BD-Store-Integration.md** - BD-Store integration plan
- **Phase-4-Uptainer-Integration.md** - Uptainer integration plan
- **Integration-Patterns.md** - Integration implementation patterns

## Maintaining the Wiki

### Regular Updates
- Update when adding new features
- Keep API documentation in sync with code
- Add troubleshooting entries for common issues
- Update version numbers and dates

### Best Practices
- Use clear, concise language
- Include code examples
- Add diagrams for complex concepts
- Link to related pages
- Keep pages focused (split large pages)
- Use consistent formatting

## Troubleshooting

### Wiki Clone Fails
If `git clone https://github.com/mylaniakea/unity.wiki.git` fails:
- Wiki doesn't exist yet - create first page via web interface
- Check repository permissions
- Verify URL (should end in `.wiki.git`)

### Push Rejected
If push is rejected:
- Pull first: `git pull origin master`
- Resolve conflicts if any
- Push again: `git push origin master`

### Links Not Working
- Ensure page names match exactly (case-sensitive)
- Use hyphens instead of spaces in filenames
- Check double-bracket syntax: `[[Page-Name]]`

## Wiki vs. Regular Docs

**Use Wiki For**:
- User-facing documentation
- Getting started guides
- API reference
- Tutorials and how-tos
- FAQs and troubleshooting

**Use Repository Docs For**:
- README.md (project overview)
- CONTRIBUTING.md (contribution guide)
- LICENSE (license information)
- Integration technical plans
- Implementation notes

## Example Commands

```bash
# Clone wiki
git clone https://github.com/mylaniakea/unity.wiki.git

# Add all pages
cd unity.wiki
git add *.md

# Commit
git commit -m "Add comprehensive documentation"

# Push
git push origin master

# Update existing page
nano Home.md
git commit -am "Update Home page"
git push
```

## Next Steps

1. ✅ Review the created wiki pages
2. ⏭️ Push wiki to GitHub using Option 2 above
3. ⏭️ Create additional pages from the recommended list
4. ⏭️ Link wiki from main README.md
5. ⏭️ Announce wiki availability to users

## Questions?

- GitHub Wiki documentation: https://docs.github.com/en/communities/documenting-your-project-with-wikis
- Markdown guide: https://guides.github.com/features/mastering-markdown/

---

**Created**: December 15, 2024
**Status**: Ready to push to GitHub
