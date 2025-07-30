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


def elevate():
    script = os.path.abspath(sys.argv[0])
    # Properly quote the script path and escape quotes for PowerShell
    powershell_cmd = f'Start-Process python -ArgumentList \'"{script}"\' -Verb runAs'
    subprocess.run(['powershell', '-Command', powershell_cmd])


def enable_password_sharing():
    subprocess.run(['powershell', '-Command', 'Set-SmbServerConfiguration -EnableSecuritySignature $true -Force'])
    print("Password protected sharing enabled.")

def disable_password_sharing():
    subprocess.run(['powershell', '-Command', 'Set-SmbServerConfiguration -EnableSecuritySignature $false -Force'])
    print("Password protected sharing disabled.")

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

def share_folders(folders, access_level):
    for folder in folders:
        folder = os.path.abspath(folder)
        share_name = os.path.basename(folder).replace(' ', '_')
        print(f"Sharing {folder} as {share_name} with {'Read-only' if access_level == 'R' else 'Read/Write'} access...")

        check_cmd = f"Get-SmbShare -Name '{share_name}'"
        check_result = subprocess.run(['powershell', '-Command', check_cmd], capture_output=True, text=True)

        if check_result.returncode == 0:
            print(f"⚠️ Share name '{share_name}' already exists.")
            choice = input("Do you want to remove and recreate it? (y/n): ").strip().lower()
            if choice == 'y':
                subprocess.run(['powershell', '-Command', f'Remove-SmbShare -Name "{share_name}" -Force'])
            else:
                print("Skipping this folder.")
                continue

        subprocess.run(['powershell', '-Command', f'icacls "{folder}" /grant Everyone:"(OI)(CI){access_level}"'])

def revoke_folders():
    folders = select_folders()
    for folder in folders:
        folder = os.path.abspath(folder)
        share_name = os.path.basename(folder).replace(' ', '_')
        print(f"Revoking share {share_name}...")
        subprocess.run(['powershell', '-Command', f'Remove-SmbShare -Name "{share_name}" -Force'])
        subprocess.run(['powershell', '-Command', f'icacls "{folder}" /remove Everyone'])

def main_menu():
    while True:
        print("""
Welcome to LAN Folder Share CLI

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
            print("Goodbye!")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == '__main__':
    if not is_admin():
        print("This action requires administrator privileges.\nAttempting to relaunch as administrator...")
        elevate()
        sys.exit()
    main_menu()
