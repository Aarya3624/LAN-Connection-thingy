import os
import sys
import ctypes
import subprocess
import tkinter as tk
from tkinter import filedialog

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate_and_restart():
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([f'"{arg}"' for arg in sys.argv])
    powershell_cmd = f"""Start-Process python -ArgumentList '{params}' -Verb runAs"""
    subprocess.run(['powershell', '-Command', powershell_cmd])
    sys.exit()


def ensure_private_network():
    print("\n🌐 Checking current network profile...")
    profile_check = subprocess.run([
        'powershell', '-Command', 
        "(Get-NetConnectionProfile).NetworkCategory"
    ], capture_output=True, text=True)

    category = profile_check.stdout.strip()
    if category == "Public":
        print("⚠️ Your network is set to Public.")
        consent = input("Would you like to switch it to Private so folder sharing works? (y/n): ").strip().lower()
        if consent == 'y':
            result = subprocess.run([
                'powershell', '-Command', 
                "Get-NetConnectionProfile | Set-NetConnectionProfile -NetworkCategory Private"
            ])
            if result.returncode == 0:
                print("✅ Network category set to Private.")
            else:
                print("❌ Failed to change network category. Try running this script as administrator.")
        else:
            print("Sharing may not work on a Public network.")
    else:
        print("✅ Network is already set to Private.")

def enable_password_sharing():
    subprocess.run(['powershell', '-Command', 'Set-SmbServerConfiguration -EnableSecuritySignature $true -Force'])
    print("✅ Password protected sharing enabled.")

def disable_password_sharing():
    subprocess.run(['powershell', '-Command', 'Set-SmbServerConfiguration -EnableSecuritySignature $false -Force'])
    print("✅ Password protected sharing disabled.")

def select_folders():
    root = tk.Tk()
    root.withdraw()
    folders = []
    while True:
        folder = filedialog.askdirectory(title="Select a folder to share")
        if folder:
            folders.append(folder)
        else:
            break
        more = input("Add another folder? (y/n): ").lower()
        if more != 'y':
            break
    return folders

def grant_folder_permission(folder, access_level):
    subprocess.run(['icacls', folder, '/remove:g', 'Everyone'])
    if access_level == 'R':
        subprocess.run(['icacls', folder, '/grant:r', 'Everyone:(OI)(CI)(GR)'])
    else:
        subprocess.run(['icacls', folder, '/grant:r', 'Everyone:(OI)(CI)(F)'])

def share_folders(folders, access_level):
    for folder in folders:
        folder = os.path.abspath(folder)
        share_name = os.path.basename(folder).replace(' ', '_')
        print(f"Sharing {folder} as {share_name} with {'Read-only' if access_level == 'R' else 'Read/Write'} access...")

        check_cmd = f"Get-SmbShare -Name '{share_name}'"
        check_result = subprocess.run(['powershell', '-Command', check_cmd], capture_output=True, text=True)

        if "Name" in check_result.stdout:
            print(f"⚠️ Share name '{share_name}' already exists.")
            choice = input("Do you want to remove and recreate it? (y/n): ").strip().lower()
            if choice == 'y':
                subprocess.run(['powershell', '-Command', f'Remove-SmbShare -Name \"{share_name}\" -Force'])
            else:
                print("Skipping this folder.")
                continue

        permission = "(OI)(CI)(RX)" if access_level == 'R' else "(OI)(CI)F"
        subprocess.run(['powershell', '-Command', f'icacls \"{folder}\" /grant Everyone:\"{permission}\"'])

        if access_level == 'R':
            share_cmd = f"New-SmbShare -Name \"{share_name}\" -Path \"{folder}\" -ReadAccess 'Everyone'"
        else:
            share_cmd = f"New-SmbShare -Name \"{share_name}\" -Path \"{folder}\" -FullAccess 'Everyone'"

        result = subprocess.run(['powershell', '-Command', share_cmd], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Shared '{folder}' as '{share_name}'")
        else:
            print(f"❌ Failed to share: {result.stderr}")

def revoke_folders():
    folders = select_folders()
    for folder in folders:
        folder = os.path.abspath(folder)
        share_name = os.path.basename(folder).replace(' ', '_')
        print(f"🛑 Revoking share '{share_name}'...")
        subprocess.run(['powershell', '-Command', f'Remove-SmbShare -Name "{share_name}" -Force'])
        subprocess.run(['icacls', folder, '/remove:g', 'Everyone'])

def main_menu():
    ensure_private_network()
    while True:
        print("""
🔧 Welcome to LAN Folder Share CLI

1. Enable password-protected sharing
2. Disable password-protected sharing
3. Share folder(s)
4. Stop sharing folder(s)
5. Exit
""")
        choice = input("Choose an option [1-5]: ").strip()

        if choice == '1':
            enable_password_sharing()
        elif choice == '2':
            disable_password_sharing()
        elif choice == '3':
            folders = select_folders()
            level = input("Select access level: [1] Read-only [2] Read/Write: ").strip()
            access_level = 'R' if level == '1' else 'F'
            share_folders(folders, access_level)
        elif choice == '4':
            revoke_folders()
        elif choice == '5':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option. Please try again.")

if __name__ == '__main__':
    if not is_admin():
        print("🔐 This action requires administrator privileges.\nAttempting to relaunch as administrator...")
        elevate_and_restart()
    else:
        main_menu()
