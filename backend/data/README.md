# Data Directory

This directory contains runtime data files that should NOT be committed to Git.

## Required Files

### SSH Keys
Generate SSH keys for homelab access:
```bash
ssh-keygen -t rsa -b 4096 -f homelab_id_rsa -N ""
```

### Database
The SQLite database (`homelab.db`) will be created automatically on first run.

## Files in this directory
- `homelab_id_rsa` - SSH private key (DO NOT COMMIT)
- `homelab_id_rsa.pub` - SSH public key (DO NOT COMMIT)
- `homelab.db` - SQLite database (DO NOT COMMIT)

All these files are ignored by `.gitignore`.
