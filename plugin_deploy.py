import os
import paramiko
import zipfile
import json
import argparse
import shutil
import locale
import re
from datetime import datetime
from scp import SCPClient
from dotenv import load_dotenv
import tempfile

def load_version_info():
    version_file = os.path.join('upload-suite-data', 'deploy_versions.json')
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            return json.load(f)
    return {
        'current_version': '1.0.0',
        'deployments': []
    }

def ensure_backup_dir():
    """Ensure the backup directory exists."""
    backup_dir = os.path.join('upload-suite-data', 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def save_version_info(version_info):
    os.makedirs('upload-suite-data', exist_ok=True)
    version_file = os.path.join('upload-suite-data', 'deploy_versions.json')
    with open(version_file, 'w') as f:
        json.dump(version_info, f, indent=2)

def get_next_version(current_version, is_minor=False, is_major=False):
    major, minor, patch = map(int, current_version.split('.'))
    
    if is_major:
        return f"{major + 1}.0.0"
    elif is_minor:
        return f"{major}.{minor + 1}.0"
    else:
        return f"{major}.{minor}.{patch + 1}"

def get_readable_timestamp():
    try:
        locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
    except:
        locale.setlocale(locale.LC_TIME, 'en_US')
    
    now = datetime.now()
    day = now.day
    if 4 <= day <= 20 or 24 <= day <= 30:
        day_suffix = 'th'
    else:
        day_suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    
    return now.strftime(f"%A {day}{day_suffix} %B %I:%M:%S%p").lower()

def create_ssh_client(server, port, user, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port=port, username=user, password=password)
    return client

def zip_directory(directory_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(directory_path):
            if '.git' in dirs:
                dirs.remove('.git')
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, directory_path)
                zipf.write(file_path, arcname)
    print(f"Created zip file: {zip_path}")

def update_plugin_version(version_str, local_dir):
    """Update the version number in the main plugin file."""
    plugin_file = os.path.join(local_dir, 'syncModule-suite.php')
    
    print(f"🔍 Updating version in: {plugin_file}")
    
    if not os.path.exists(plugin_file):
        print(f"❌ Plugin file not found: {plugin_file}")
        return False
    
    try:
        with open(plugin_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update version in plugin header
        content = re.sub(
            r'(Version:\s*)\d+\.\d+\.\d+',
            lambda m: m.group(1) + version_str,
            content
        )
        
        # Update version constant
        content = re.sub(
            r"(define\('syncModule_SUITE_VERSION',\s*')\d+\.\d+\.\d+('\))",
            lambda m: m.group(1) + version_str + m.group(2),
            content
        )
        
        with open(plugin_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Updated plugin version to: {version_str}")
        return True
            
    except Exception as e:
        print(f"❌ Failed to update plugin version: {str(e)}")
        import traceback
        print(f"🔍 Error details: {traceback.format_exc()}")
        return False

def download_current_version(server, port, username, password, site='woven', local_download_dir='data'):
    """Download the current version of the plugin from the server."""
    try:
        os.makedirs(local_download_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"syncModule-suite-{site}-backup-{timestamp}.zip"
        local_zip_path = os.path.join(local_download_dir, zip_filename)
        
        print(f"🔍 Connecting to {site} server to download current version...")
        ssh = create_ssh_client(server, port, username, password)
        
        temp_dir = f"/tmp/syncModule-suite-backup-{timestamp}"
        remote_base_dir = f"domains/syncModule{site}.com/public_html/wp-content/plugins/syncModule-suite"
        
        commands = [
            f"mkdir -p {temp_dir}",
            f"cp -r {remote_base_dir}/* {temp_dir}/",
            f"cd {os.path.dirname(temp_dir)} && zip -r {temp_dir}.zip {os.path.basename(temp_dir)}",
            f"rm -rf {temp_dir}"
        ]
        
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            if stdout.channel.recv_exit_status() != 0:
                print(f"⚠️  Warning: Command failed: {cmd}")
        
        scp = SCPClient(ssh.get_transport())
        print(f"⬇️  Downloading current version from server...")
        scp.get(f"{temp_dir}.zip", local_zip_path)
        
        ssh.exec_command(f"rm {temp_dir}.zip")
        
        print(f"✅ Successfully downloaded current version to: {local_zip_path}")
        return local_zip_path
        
    except Exception as e:
        print(f"❌ Failed to download current version: {str(e)}")
        return None
    finally:
        if 'scp' in locals():
            scp.close()
        if 'ssh' in locals():
            ssh.close()

def main():
    parser = argparse.ArgumentParser(description='Deploy syncModule Suite')
    parser.add_argument('-m', '--patch', action='store_true', help='Create a patch version (x.y.z+1)')
    parser.add_argument('-M', '--minor', action='store_true', help='Create a minor version (x.y+1.0)')
    parser.add_argument('-S', '--major', action='store_true', help='Create a major version (x+1.0.0)')
    parser.add_argument('-l', '--message', help='Add a deployment message')
    parser.add_argument('-d', '--download', action='store_true', help='Download current version from server')
    args = parser.parse_args()

    version_info = load_version_info()
    current_version = version_info.get('current_version', '1.0.0')
    
    if args.major:
        version_str = get_next_version(current_version, is_major=True)
        version_type = 'major'
    elif args.minor:
        version_str = get_next_version(current_version, is_minor=True)
        version_type = 'minor'
    else:
        version_str = get_next_version(current_version)
        version_type = 'patch'

    print(f"🚀 Deploying syncModule Suite version: {version_str} ({version_type} update)")

    load_dotenv()
    
    # Server Configuration (Use .env)
    server = os.getenv('REMOTE_SERVER', 'your-server')
    port = int(os.getenv('REMOTE_PORT', '65002'))
    username = os.getenv('REMOTE_USER', 'your-username')
    password = os.getenv('REMOTE_PASS', 'your-password')
    
    if args.download:
        download_current_version(server, port, username, password, site='woven')
        download_current_version(server, port, username, password, site='knit')
        return
    
    local_dir = os.path.join(os.getcwd(), "syncModule-suite")
    
    if not os.path.exists(local_dir):
        print(f"❌ Error: Local directory not found: {local_dir}")
        return
    
    if not update_plugin_version(version_str, local_dir):
        print("⚠️  Continuing without updating plugin version...")
    
    print("📦 Creating zip file...")
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a sanitized version of the message for the filename
        safe_message = ''
        if args.message:
            # Replace spaces with underscores and remove special characters
            safe_message = '-' + re.sub(r'[^\w-]', '', args.message.replace(' ', '_').lower())
            # Limit message length to 50 characters
            safe_message = safe_message[:50]
            
        zip_filename = f"syncModule-suite-{version_str}{safe_message}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)
        zip_directory(local_dir, zip_path)
        
        # Create local backup
        backup_dir = ensure_backup_dir()
        backup_path = os.path.join(backup_dir, zip_filename)
        shutil.copy2(zip_path, backup_path)
        print(f"💾 Created local backup: {backup_path}")
        
        # Deploy to both sites
        success = True
        for site in ['woven', 'knit']:
            if not deploy_to_server(server, port, username, password, zip_path, version_str, site, version_type, args.message):
                success = False
        
        if success:
            # Update version info only if all deployments were successful
            version_info['current_version'] = version_str
            deployment = {
                'version': version_str,
                'type': version_type,
                'timestamp': datetime.now().isoformat(),
                'message': args.message if args.message else '',
                'backup_file': os.path.join('backups', zip_filename)
            }
            version_info['deployments'].append(deployment)
            save_version_info(version_info)
            print(f"✅ Successfully deployed syncModule Suite {version_str} to both sites")
        else:
            print("❌ One or more deployments failed. Check logs for details.")
            return 1
    
    return 0

def deploy_to_server(server, port, username, password, local_zip_path, version_str, site, version_type, message):
    """Deploy the plugin to a specific site."""
    remote_base_dir = f"domains/syncModule{site}.com/public_html/wp-content/plugins/syncModule-suite"
    print(f"🚀 Uploading to syncModule{site}.com...")
    
    try:
        ssh = create_ssh_client(server, port, username, password)
        scp = SCPClient(ssh.get_transport())
        
        # Create remote directory if it doesn't exist
        ssh.exec_command(f'mkdir -p {remote_base_dir}')
        
        # Upload the zip file
        remote_zip_path = f"/tmp/syncModule-suite-{version_str}.zip"
        scp.put(local_zip_path, remote_zip_path)
        
        # Extract the new version
        ssh.exec_command(f'unzip -o {remote_zip_path} -d {os.path.dirname(remote_base_dir)}')
        ssh.exec_command(f'rm {remote_zip_path}')
        
        # Set correct permissions
        ssh.exec_command(f'chmod -R 755 {remote_base_dir}')
        ssh.exec_command(f'chown -R {username}:{username} {remote_base_dir}')
        
        print(f"✅ Successfully deployed syncModule Suite {version_str} to syncModule{site}.com")
        return True
        
    except Exception as e:
        print(f"❌ Deployment to syncModule{site}.com failed: {str(e)}")
        import traceback
        print(f"🔍 Error details: {traceback.format_exc()}")
        return False
    finally:
        if 'scp' in locals():
            scp.close()
        if 'ssh' in locals():
            ssh.close()

if __name__ == "__main__":
    main()
