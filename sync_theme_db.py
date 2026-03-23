#!/usr/bin/env python3
"""
Dehati Project - Hostinger Deployment Script
Deploys WordPress theme, media files, and database to Hostinger staging
"""

import os
import paramiko
import argparse
import shutil
from scp import SCPClient
from datetime import datetime
import zipfile
import tempfile

# Hostinger SSH Configuration
# Configuration (Use .env or specify manually)
HOST_CONFIG = {
    'host': os.getenv('REMOTE_HOST', 'your-host-ip'),
    'port': int(os.getenv('REMOTE_PORT', '65002')),
    'username': os.getenv('REMOTE_USER', 'your-username'),
    'password': os.getenv('REMOTE_PASS', 'your-password'),
    'remote_base': os.getenv('REMOTE_PATH', 'domains/example.com/public_html')
}

# Local paths
LOCAL_THEME_PATH = os.getenv('LOCAL_THEME_PATH', "./theme")
LOCAL_UPLOADS_PATH = os.getenv('LOCAL_UPLOADS_PATH', "./uploads")

def create_ssh_client():
    """Create and return an SSH client connection to Hostinger."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST_CONFIG['host'],
        port=HOST_CONFIG['port'],
        username=HOST_CONFIG['username'],
        password=HOST_CONFIG['password']
    )
    return client

def exec_ssh_command(ssh, command, description=""):
    """Execute SSH command and return output."""
    if description:
        print(f"🔧 {description}")
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    
    if exit_status != 0:
        print(f"⚠️  Command failed: {command}")
        if error:
            print(f"   Error: {error}")
    return exit_status, output, error

def sync_theme(ssh, scp):
    """Sync the WordPress theme to Hostinger."""
    print("\n📦 Syncing WordPress Theme...")
    
    remote_theme_path = f"{HOST_CONFIG['remote_base']}/wp-content/themes/dehati-theme-2026"
    
    # Create backup of existing theme
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{remote_theme_path}_backup_{timestamp}"
    
    exec_ssh_command(
        ssh,
        f"[ -d {remote_theme_path} ] && cp -r {remote_theme_path} {backup_path} || echo 'No existing theme'",
        "Creating backup of existing theme"
    )
    
    # Create temporary zip of theme
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, 'dehati-theme-2026.zip')
        print(f"📦 Creating theme archive...")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(LOCAL_THEME_PATH):
                # Skip .git and node_modules
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '.DS_Store']]
                
                for file in files:
                    if file == '.DS_Store':
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, LOCAL_THEME_PATH)
                    zipf.write(file_path, arcname)
        
        # Upload zip
        remote_zip = f"/tmp/dehati-theme-{timestamp}.zip"
        print(f"⬆️  Uploading theme archive...")
        scp.put(zip_path, remote_zip)
        
        # Extract on server
        exec_ssh_command(
            ssh,
            f"mkdir -p {remote_theme_path} && unzip -o {remote_zip} -d {remote_theme_path}",
            "Extracting theme on server"
        )
        
        # Cleanup
        exec_ssh_command(ssh, f"rm {remote_zip}", "Cleaning up temporary files")
    
    print("✅ Theme sync complete")

def sync_media(ssh, scp):
    """Sync media files (uploads directory) to Hostinger."""
    print("\n📸 Syncing Media Files...")
    
    remote_uploads_path = f"{HOST_CONFIG['remote_base']}/wp-content/uploads"
    
    # Create uploads directory if it doesn't exist
    exec_ssh_command(ssh, f"mkdir -p {remote_uploads_path}", "Creating uploads directory")
    
    # Create temporary zip of uploads
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, 'uploads.zip')
        print(f"📦 Creating media archive...")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(LOCAL_UPLOADS_PATH):
                dirs[:] = [d for d in dirs if d != '.DS_Store']
                
                for file in files:
                    if file == '.DS_Store':
                        continue
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, LOCAL_UPLOADS_PATH)
                    zipf.write(file_path, arcname)
        
        # Upload zip
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        remote_zip = f"/tmp/uploads-{timestamp}.zip"
        print(f"⬆️  Uploading media archive...")
        scp.put(zip_path, remote_zip)
        
        # Extract on server
        exec_ssh_command(
            ssh,
            f"unzip -o {remote_zip} -d {remote_uploads_path}",
            "Extracting media files on server"
        )
        
        # Cleanup
        exec_ssh_command(ssh, f"rm {remote_zip}", "Cleaning up temporary files")
    
    print("✅ Media sync complete")

def upload_database(ssh, scp, db_file, auto_import=False):
    """Upload and import database file."""
    print("\n💾 Uploading Database...")
    
    if not os.path.exists(db_file):
        print(f"❌ Database file not found: {db_file}")
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    remote_db_path = f"/tmp/dehati-db-{timestamp}.sql"
    
    # Upload database file
    print(f"⬆️  Uploading database file...")
    scp.put(db_file, remote_db_path)
    
    print(f"✅ Database uploaded to: {remote_db_path}")
    
    if auto_import:
        print(f"🔄 Importing database on server...")
        import_cmd = f"wp db import {remote_db_path} --path={HOST_CONFIG['remote_base']}"
        status, output, error = exec_ssh_command(ssh, import_cmd, "Importing database")
        
        if status == 0:
            print(f"✅ Database imported successfully")
            # Cleanup remote SQL file after successful import
            exec_ssh_command(ssh, f"rm {remote_db_path}", "Cleaning up remote SQL file")
        else:
            print(f"❌ Database import failed. Please check manually.")
            print(f"   Command: {import_cmd}")
    else:
        print(f"\n📝 To import the database, run this command on the server:")
        print(f"   wp db import {remote_db_path} --path={HOST_CONFIG['remote_base']}")
        print(f"\n   Or use phpMyAdmin to import: {remote_db_path}")
    
    return True

def clear_cache(ssh):
    """Clear LiteSpeed cache on the server."""
    print("\n🧹 Clearing Cache...")
    
    wp_path = HOST_CONFIG['remote_base']
    
    # Try to clear LiteSpeed cache
    exec_ssh_command(
        ssh,
        f"cd {wp_path} && wp litespeed-purge all 2>/dev/null || echo 'LiteSpeed cache not available'",
        "Clearing LiteSpeed cache"
    )
    
    # Clear object cache
    exec_ssh_command(
        ssh,
        f"cd {wp_path} && wp cache flush 2>/dev/null || echo 'Cache flush not available'",
        "Flushing object cache"
    )
    
    print("✅ Cache cleared")

def main():
    parser = argparse.ArgumentParser(description='Deploy Dehati Project to Hostinger')
    parser.add_argument('--theme', action='store_true', help='Deploy theme files')
    parser.add_argument('--media', action='store_true', help='Deploy media files')
    parser.add_argument('--db', type=str, help='Path to database SQL file to upload')
    parser.add_argument('--import-db', action='store_true', help='Automatically import database after upload')
    parser.add_argument('--all', action='store_true', help='Deploy everything (theme + media)')
    parser.add_argument('--clear-cache', action='store_true', help='Clear server cache')
    
    args = parser.parse_args()
    
    # If no specific flags, show help
    if not (args.theme or args.media or args.db or args.all or args.clear_cache):
        parser.print_help()
        print("\n💡 Example usage:")
        print("   python deploy_dehati.py --all")
        print("   python deploy_dehati.py --theme")
        print("   python deploy_dehati.py --db /path/to/database.sql")
        return
    
    print("🚀 Dehati Project Deployment to Hostinger")
    print(f"   Target: {HOST_CONFIG['host']}")
    print(f"   Site: https://dehatifest.com/\n")
    
    try:
        # Create SSH connection
        print("🔌 Connecting to Hostinger...")
        ssh = create_ssh_client()
        scp = SCPClient(ssh.get_transport())
        print("✅ Connected\n")
        
        # Deploy theme
        if args.theme or args.all:
            sync_theme(ssh, scp)
        
        # Deploy media
        if args.media or args.all:
            sync_media(ssh, scp)
        
        # Upload database
        if args.db:
            upload_database(ssh, scp, args.db, args.import_db)
        
        # Clear cache
        if args.clear_cache or args.all:
            clear_cache(ssh)
        
        print("\n✅ Deployment complete!")
        print(f"   Visit: https://dehatifest.com/")
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if 'scp' in locals():
            scp.close()
        if 'ssh' in locals():
            ssh.close()
    
    return 0

if __name__ == "__main__":
    exit(main())
