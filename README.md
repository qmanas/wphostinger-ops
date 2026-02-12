# 🚀 WPHostinger Ops: Automated WordPress CI/CD for Hostinger

**WPHost** is a collection of high-performance Python scripts designed to automate the deployment, synchronization, and versioning of WordPress themes, plugins, and databases for the **Hostinger** ecosystem. This suite eliminates the risk of manual sync errors and provides a professional CI/CD-like workflow for WordPress development.

---

## 🔥 Problem: Manual FTP and DB Synchronization
WordPress deployment is traditionally manual (FTP + phpMyAdmin), which is slow, error-prone, and lacks version control. **WPHost** provides a **Push-to-Deploy** experience, handling file-zipping, SSH transport, remote extraction, permission hardening, and database imports in a single command.

---

## 🛡️ Architecture: High-Integrity Sync
1.  **Transactional Plugin Deployment**: Automatically increments version numbers in plugin headers and definitions before creating version-tracked backups and pushing to multiple production sites.
2.  **Theme & Media Synchronization**: Performs a deep sync of `/themes/` and `/uploads/` directories using secure SSH/SCP, including automatic remote backup generation before any overwrite.
3.  **Atomic Database Migration**: Seamlessly exports local databases and imports them into remote environments via `wp-cli` over SSH, ensuring data integrity across dev, staging, and production.
4.  **Multi-Site Orchestration**: Designed to push updates to multiple domains simultaneously to keep a distributed WordPress ecosystem perfectly synchronized.

---

## 🛠️ Core Components
- **`plugin_deploy.py`**: Automated versioning and multi-site plugin deployment logic.
- **`sync_theme_db.py`**: Theme and media synchronization engine.
- **`export_database.py`**: Deterministic database export and sanitization logic.

---

## ✨ Engineering Wins
- **Zero Versioning Errors**: Eliminated the need to manually update version strings in PHP files.
- **Deployment Speed**: Reduced full-site deployment time from 15 minutes to ~40 seconds per site.
- **Disaster Recovery**: Every deployment creates a time-stamped remote backup for instant rollback capability.

---

**Built for the high-performance WordPress architect. 🛠️**
