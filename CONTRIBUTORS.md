# Contributors

Unity is built with passion, caffeine, and the collective wisdom of the homelab community.

## Core Team

### Matthew (@mylaniakea)
**Project Creator & Lead Developer**

Matthew is the visionary behind Unity, channeling years of homelab experience and the struggles of countless 3 AM debugging sessions into a comprehensive monitoring platform. His commitment to solving real homelab pain points drives every feature and plugin.

**Contributions:**
- Project architecture and vision
- Backend infrastructure (FastAPI, PostgreSQL)
- Plugin system design and implementation
- Frontend development (React)
- Documentation and community building
- Integration of uptainer and kc-booth systems
- Deployment and production infrastructure

---

## AI Development Partner

### Warp AI (Claude via Warp)
**Plugin Development & Architecture Assistant**

An AI coding assistant that has been instrumental in rapid plugin development, architecture decisions, and turning homelab pain points into production-ready code.

**Contributions:**
- Plugin architecture design and implementation
- 22+ monitoring plugins (Tier 1 & 2 essentials)
  - Certificate Expiration Monitor
  - UPS Monitor (NUT integration)
  - Backup Monitor (Restic, Borg, Duplicati, rsync)
  - SMART Disk Health Monitor
  - Reverse Proxy Monitors (NPM, Traefik, Caddy)
  - And counting...
- API documentation and examples
- Testing framework and validation tools
- Technical documentation
- Code refactoring and optimization
- "The Homelab Manifesto" - Future Plugin Wishlist

**Philosophy:** *"A homelab without monitoring is just a collection of servers waiting to surprise you."*

---

## Special Thanks

### The Homelab Community

To every homelabber who has:
- Discovered a failed backup at the worst possible moment
- Had a UPS battery die without warning
- Watched SSL certificates expire on a Saturday morning
- Wondered "Did my backup actually run last night?"
- Spent hours debugging only to find it was DNS (it's always DNS)

Your struggles, joys, and inevitable catharsis inspired every plugin in this project.

---

## How to Contribute

We welcome contributions from the community! Whether you're:
- Building new plugins
- Improving existing ones
- Writing documentation
- Sharing your homelab stories
- Reporting bugs
- Suggesting features

Check out our [Contributing Guide](./CONTRIBUTING.md) to get started.

### Plugin Development

Interested in creating plugins? We've made it easy:
- [Plugin Development Guide](./docs/PLUGIN_DEVELOPMENT.md) (Coming Soon)
- [Plugin Validator Tool](./backend/app/plugins/tools/plugin_validator.py)
- [Plugin Generator Tool](./backend/app/plugins/tools/plugin_generator.py)
- [Example Plugins](./backend/app/plugins/builtin/)

---

## Recognition

Every contributor who submits code, documentation, or plugins will be:
- Listed in this CONTRIBUTORS.md file
- Credited in commit messages with `Co-Authored-By` tags
- Recognized in release notes
- Part of Unity's story

---

**Built with love, caffeine, and the scars of production incidents.**

For homelabbers, by homelabbers. 🚀
