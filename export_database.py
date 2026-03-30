#!/usr/bin/env python3
"""
Export database from Local by Flywheel and prepare for deployment
"""

import os
import subprocess
import re
from datetime import datetime

# Paths
LOCAL_SITE_PATH = "/Users/developer/Local Sites/the-dehati-project/app/public"
LOCAL_CONF_PATH = "/Users/developer/Local Sites/the-dehati-project/conf/mysql"
OUTPUT_DIR = "/Users/developer/projects/dehati-project-wp/database-exports"

def export_database():
    """Export database using mysqldump from Local's MySQL."""
    print("💾 Exporting database from Local...")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get database credentials from wp-config.php
    wp_config_path = os.path.join(LOCAL_SITE_PATH, "wp-config.php")
    
    with open(wp_config_path, 'r') as f:
        config_content = f.read()
    
    # Extract database credentials
    db_name_match = re.search(r"define\(\s*'DB_NAME',\s*'([^']+)'\s*\)", config_content)
    db_user_match = re.search(r"define\(\s*'DB_USER',\s*'([^']+)'\s*\)", config_content)
    db_pass_match = re.search(r"define\(\s*'DB_PASSWORD',\s*'([^']+)'\s*\)", config_content)
    db_host_match = re.search(r"define\(\s*'DB_HOST',\s*'([^']+)'\s*\)", config_content)
    
    if not all([db_name_match, db_user_match, db_pass_match, db_host_match]):
        print("❌ Could not extract database credentials from wp-config.php")
        return None
    
    db_name = db_name_match.group(1)
    db_user = db_user_match.group(1)
    db_pass = db_pass_match.group(1)
    db_host = db_host_match.group(1)
    
    print(f"   Database: {db_name}")
    print(f"   Host: {db_host}")
    
    # Generate output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"dehati-local-{timestamp}.sql")
    
    # Try to find mysqldump in Local's MySQL installation
    possible_mysqldump_paths = [
        "/Applications/Local.app/Contents/Resources/extraResources/lightning-services/mysql-8.0.16+6/bin/mysqldump/darwin/bin/mysqldump",
        "/usr/local/bin/mysqldump",
        "mysqldump"
    ]
    
    mysqldump_cmd = None
    for path in possible_mysqldump_paths:
        if os.path.exists(path) or path == "mysqldump":
            mysqldump_cmd = path
            break
    
    if not mysqldump_cmd:
        print("❌ mysqldump not found. Please export database manually from Local.")
        print(f"   1. Open Local app")
        print(f"   2. Right-click 'the-dehati-project' site")
        print(f"   3. Select 'Open Site Shell'")
        print(f"   4. Run: wp db export {output_file}")
        return None
    
    # Export database
    try:
        cmd = [
            mysqldump_cmd,
            f"--host={db_host}",
            f"--user={db_user}",
            f"--password={db_pass}",
            db_name
        ]
        
        print(f"⬇️  Exporting to: {output_file}")
        
        with open(output_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"❌ Export failed: {result.stderr}")
            return None
        
        # Search and replace URLs
        print("🔄 Replacing URLs...")
        with open(output_file, 'r') as f:
            content = f.read()
        
        # Replace local URLs with staging URLs
        content = content.replace('http://the-dehati-project.local', 'https://dehatifest.com')
        content = content.replace('the-dehati-project.local', 'dehatifest.com')
        
        # Write back
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Database exported and prepared: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"❌ Export failed: {str(e)}")
        return None

if __name__ == "__main__":
    db_file = export_database()
    
    if db_file:
        print(f"\n📝 Next steps:")
        print(f"   1. Run: python deploy_dehati.py --all --db {db_file}")
        print(f"   2. Or deploy components separately:")
        print(f"      python deploy_dehati.py --theme")
        print(f"      python deploy_dehati.py --media")
        print(f"      python deploy_dehati.py --db {db_file}")
