import os
import subprocess
import platform
import socket
import threading
import ctypes
import sys


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def relaunch_as_admin():
    if not is_admin():
        print("This action requires administrator privileges.")
        print("Attempting to relaunch as administrator...")
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([f'\"{arg}\"' for arg in sys.argv[1:]])
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'\"{script}\" {params}', None, 1)
        except Exception as e:
            print("Failed to relaunch as administrator:", e)
        sys.exit(0)


def advertise_on_network():
    import socketserver
    import http.server

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

    with socketserver.TCPServer(("", 445), Handler) as httpd:
        print(f"Advertising service {socket.gethostname()} on {socket.gethostbyname(socket.gethostname())}:445")
        print("Press Enter to stop...")
        input()
        httpd.server_close()


def share_folder_windows(folder_path):
    folder_name = os.path.basename(folder_path)

    print("\nWARNING: Password protected sharing will be disabled to allow access without login credentials.")
    print("Only proceed if you are on a trusted network.\n")

    try:
        # Ensure File Sharing and Network Discovery are enabled
        subprocess.run([
            'powershell', '-Command',
            'Set-NetFirewallRule -DisplayGroup "File and Printer Sharing" -Enabled True'
        ], check=True)

        subprocess.run([
            'powershell', '-Command',
            'Set-NetFirewallRule -DisplayGroup "Network Discovery" -Enabled True'
        ], check=True)

        # Disable password protected sharing
        subprocess.run([
            'powershell', '-Command',
            'Set-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa" -Name "LimitBlankPasswordUse" -Value 0'
        ], check=True)

        subprocess.run([
            'powershell', '-Command',
            'Set-SmbServerConfiguration -EnableSecuritySignature $false -Force'
        ], check=True)

        subprocess.run([
            'powershell', '-Command',
            'Set-SmbServerConfiguration -RequireSecuritySignature $false -Force'
        ], check=True)

        # Create the share with Everyone having full access
        subprocess.run([
            'powershell', '-Command',
            f"New-SmbShare -Name '{folder_name}' -Path '{folder_path}' -FullAccess 'Everyone'"
        ], check=True)

        # Set NTFS permissions for Everyone
        subprocess.run([
            'powershell', '-Command',
            f'icacls "{folder_path}" /grant Everyone:"(OI)(CI)F"'
        ], check=True)



        return True
    except subprocess.CalledProcessError as e:
        print("Error configuring or sharing folder:", e)
        input("Press Enter to exit...")
        return False


def main():
    relaunch_as_admin()

    os_name = platform.system()
    print(f"Detected OS: {os_name}")

    folder_path = input("Enter full path of folder to share: ").strip()

    if os_name == "Windows":
        success = share_folder_windows(folder_path)
        if success:
            advertise_on_network()
    else:
        print("This script currently supports only Windows.")

    input("\nProcess complete. Press Enter to exit...")


if __name__ == "__main__":
    main()

