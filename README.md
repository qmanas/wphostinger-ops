# 🚀 WPHostinger Ops: Automated WordPress Sync & Deploy

A Python-based deployment and sync suite for Hostinger. This collection of scripts automates the versioning and synchronization of WordPress themes, plugins, and databases, reducing manual errors during deployment.

- ⚙️ **Theme/Plugin Sync**: Logic for pushing and pulling local files to a Hostinger server.
- 🧪 **Database Migration**: Automates the export and import of WordPress databases with site-URL rewriting.
- 📦 **Versioning**: Simple version tracking for plugin/theme releases.

### Usage
- `sync_theme_db.py`: Synchronizes the current theme files and local database to the production environment.
- `plugin_deploy.py`: Pushes a specific plugin version to Hostinger with automated version incrementing.

**Deployment Model:**
- Designed for developers who prefer a CLI-based workflow over Hostinger's manual file manager.
- Requires environment variables (SSH_HOST, SSH_USER) to be configured in a `.env` file.
