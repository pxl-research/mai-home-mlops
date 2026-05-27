# Prerequirements to execute script:
# ----------------------------------
# 0) Use Linux, Linux VM (in case of MacOS) or WSL on Windows as your host machine!
# 1) Install Azure CLI on your host machine:
# curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
# 2) Install sshpass on your (Linux) host machine:
# sudo apt install sshpass -y

# Execute script and aftermath (which in future can be part of script):
# ---------------------------------------------------------------------
# 1) Login to Azure:
# az login --use-device-code
#
# 2) Execute this script on your (Linux) host machine:
# python3 infrastructure_azure_create.py
#
# 3) Generate a GitHub Personal Access Token (PAT):
# Go to GitHub > Settings (after clicking your profile picture) > Developer settings (at the bottom) > Personal access tokens > Tokens (classic).
# Or: https://github.com/settings/tokens
# Click Generate new token (classic).
# Give it a descriptive name (e.g., ghcr_token_pixie).
# Set an expiration (e.g., No Expiration).
# Important: check the write:packages scope!
# Click Generate token.
# Copy the generated token immediately because it will disappear!
#
# 4) Build and push all your Docker containers to Github Container Registry:
# echo <YOUR_GITHUB_PAT> | docker login ghcr.io -u <YOUR_GITHUB_USERNAME> --password-stdin
# docker build -t <CONTAINER_NAME> .
# docker tag <CONTAINER_NAME>:latest ghcr.io/<YOUR_GITHUB_USERNAME>/<CONTAINER_NAME>:v1
# docker push ghcr.io/<YOUR_GITHUB_USERNAME>/<CONTAINER_NAME>:v1
# Go to: https://github.com/users/<YOUR_GITHUB_USERNAME>/packages/ select the container image, go to settings and set visibility to Public if needed.
#
# 5) SSH into the VM via: ssh ADMIN_USERNAME@PUBLIC_VM_IP_ADDRESS
#
# 6) Pull and run all your Docker containers from Github Container Registry:
# NOTE: make sure .env files get on VM as well by making sure they are part of the Docker image!
# echo <YOUR_GITHUB_PAT>  | docker login ghcr.io -u <YOUR_GITHUB_USERNAME> --password-stdin
# docker pull ghcr.io/<YOUR_GITHUB_USERNAME>/<CONTAINER_NAME>:v1
# docker run -d -p 80:8080 --name <CONTAINER_NAME> ghcr.io/<YOUR_GITHUB_USERNAME>/<CONTAINER_NAME>:v1
# 7) Open your web browser and navigate to http://<YOUR_VM_PUBLIC_IP> (if frontend is mapped to port 80)


# No external dependencies except Azure CLI!
import getpass
import os
import subprocess
import sys
import time

# --- Configuration ---
RESOURCE_GROUP_NAME = "pixie_instore_ai"  # "azurevmtest" # "pixie_demo"
VM_NAME = "cretskens_pixie_vm"  # "pixie_vm"
VM_PUBLIC_PORTS = [3000] # 3001
LOCATION = "westeurope"
ADMIN_USERNAME = "azureuser"  # NOTE: is this okay for Pixie?
ADMIN_PASSWORD = (
    ""  # We define this via user input at the start of the script for security reasons
)
GPU_USED = False
if GPU_USED:
    VM_SIZE = "Standard_NC4as_T4_v3"  # Ensure this VM size is available in your region and subscription
else:
    VM_SIZE = "Standard_B2s"  # Ensure this VM size is available in your region and subscription

# --- Azure CLI Wrapper Functions ---
def az_run_command(
    command_parts: list, success_message: str, error_message: str
) -> tuple[bool, str | None]:
    """
    Executes an Azure CLI command using subprocess.run.

    Args:
        command_parts (list): A list of strings representing the command and its arguments.
        success_message (str): Message to print if the command succeeds.
        error_message (str): Message to print if the command fails. Pxl!20252025

    Returns:
        tuple[bool, str | None]: A tuple where the first element is True for success, False for failure,
                                 and the second element is the stdout string or None.
    """
    try:
        result = subprocess.run(
            command_parts, check=True, capture_output=True, text=True, shell=False
        )
        print(f"Success: {success_message}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")

        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {error_message}")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"Return Code: {e.returncode}")
        print(f"STDOUT:\n{e.stdout}")
        print(f"STDERR:\n{e.stderr}")

        return False, e.stderr  # Return stderr on failure for more info if needed
    except FileNotFoundError:
        print("Error: Azure CLI (az) command not found.")
        print("Please ensure Azure CLI is installed and in your system's PATH.")
        sys.exit(1)  # This is a critical setup error, so we exit
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}")

        return False, str(e)


def az_resource_group_exists(name: str) -> bool:
    """
    Checks if an Azure Resource Group exists.

    Args:
        name (str): The name of the resource group.

    Returns:
        bool: True if the resource group exists, False otherwise.
    """
    print(f"Checking if resource group '{name}' exists...")
    command = [
        "az",
        "group",
        "show",
        "--name",
        name,
        "--query",
        "name",
        "--output",
        "tsv",
    ]
    # We expect a non-zero exit code if the group doesn't exist,
    # so we run it directly without check=True and inspect the return code.
    try:
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, shell=False
        )
        if result.returncode == 0 and result.stdout.strip() == name:
            print(f"Resource group '{name}' already exists.")
            return True
        else:
            print(f"Resource group '{name}' does not exist.")
            return False
    except FileNotFoundError:
        print(
            "Error: Azure CLI (az) command not found. Please ensure it's installed and in PATH."
        )
    except Exception as e:
        print(f"Error checking resource group existence: {e}")

    return False


def az_vm_exists(resource_group: str, vm_name: str) -> bool:
    """
    Checks if an Azure Virtual Machine exists in a given resource group.

    Args:
        resource_group (str): The name of the resource group the VM is in.
        vm_name (str): The name of the VM.

    Returns:
        bool: True if the VM exists, False otherwise.
    """
    print(f"Checking if VM '{vm_name}' exists in resource group '{resource_group}'...")
    command = [
        "az",
        "vm",
        "show",
        "--resource-group",
        resource_group,
        "--name",
        vm_name,
        "--query",
        "name",
        "--output",
        "tsv",
    ]
    try:
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, shell=False
        )
        if result.returncode == 0 and result.stdout.strip() == vm_name:
            print(f"Virtual Machine '{vm_name}' already exists.")
            return True
        else:
            print(f"Virtual Machine '{vm_name}' does not exist.")
            return False
    except FileNotFoundError:
        print(
            "Error: Azure CLI (az) command not found. Please ensure it's installed and in PATH."
        )
    except Exception as e:
        print(f"Error checking VM existence: {e}")

    return False


def az_create_resource_group(name: str, location: str) -> bool:
    """
    Creates an Azure Resource Group.

    Args:
        name (str): The name of the resource group.
        location (str): The Azure region for the resource group.

    Returns:
        bool: True if the resource group was created successfully (or already exists), False otherwise.
    """
    print(f"Attempting to create resource group '{name}' in '{location}'...")
    command = ["az", "group", "create", "--name", name, "--location", location]
    success, _ = az_run_command(
        command,
        f"Resource group '{name}' created successfully (or already exists).",
        f"Failed to create resource group '{name}'.",
    )

    return success


def az_create_vm(
    resource_group: str,
    vm_name: str,
    image: str,
    admin_username: str,
    admin_password: str,
    public_ip_sku: str,
    public_ip_address_name: str,
    location: str,
    vm_size: str,
    security_type: str,
    enable_secure_boot: bool,
    enable_vtpm: bool,
    os_disk_size_gb: int = None, # New parameter for OS disk size
) -> bool:
    """
    Creates an Azure Virtual Machine.

    Args:
        resource_group (str): The name of the resource group.
        vm_name (str): The name of the VM.
        image (str): The VM image URN or alias (e.g., 'Ubuntu2404').
        admin_username (str): The administrator username.
        admin_password (str): The administrator password.
        public_ip_sku (str): SKU for the public IP (e.g., 'Standard').
        public_ip_address_name (str): Name for the public IP address resource.
        location (str): The Azure region for the VM.
        vm_size (str): The size of the VM (e.g., 'Standard_NC4as_T4_v3').
        security_type (str): The security type (e.g., 'TrustedLaunch').
        enable_secure_boot (bool): Whether to enable secure boot.
        enable_vtpm (bool): Whether to enable vTPM.
        os_disk_size_gb (int, optional): The size of the OS disk in GB. If not specified,
                                         the default size for the chosen image will be used.

    Returns:
        bool: True if the VM was created successfully, False otherwise.
    """
    print(
        f"Attempting to create VM '{vm_name}' in resource group '{resource_group}'..."
    )
    command = [
        "az",
        "vm",
        "create",
        "--resource-group",
        resource_group,
        "--name",
        vm_name,
        "--image",
        image,
        "--admin-username",
        admin_username,
        "--admin-password",
        admin_password,
        "--public-ip-sku",
        public_ip_sku,
        "--public-ip-address",
        public_ip_address_name,
        "--location",
        location,
        "--security-type",
        security_type,
        "--enable-secure-boot",
        str(enable_secure_boot).lower(),
        "--enable-vtpm",
        str(enable_vtpm).lower(),
        "--size",
        vm_size,
    ]

    # Add OS disk size if specified
    if os_disk_size_gb is not None:
        command.extend(["--os-disk-size-gb", str(os_disk_size_gb)])

    # The AZ CLI automatically creates a VNet, Subnet, and Network Interface
    # if they don't exist when you run 'az vm create'.
    success, _ = az_run_command(
        command,
        f"Virtual Machine '{vm_name}' created successfully.",
        f"Failed to create Virtual Machine '{vm_name}'.",
    )

    return success


def az_open_vm_port(
    resource_group: str, vm_name: str, ports: list[int], initial_priority: int
) -> bool:
    """
    Opens multiple ports on the VM's Network Security Group.

    Args:
        resource_group (str): The name of the resource group.
        vm_name (str): The name of the VM.
        ports (list[int]): A list of port numbers to open (e.g., [80, 443]).
        initial_priority (int): The starting priority for the NSG rules.
                                Priorities will increment for each port.

    Returns:
        bool: True if all ports were opened successfully, False otherwise.
    """
    all_successful = True
    current_priority = initial_priority
    for port in ports:
        print(
            f"Attempting to open port '{port}' with priority '{current_priority}' on VM '{vm_name}'..."
        )
        command = [
            "az",
            "vm",
            "open-port",
            "--resource-group",
            resource_group,
            "--name",
            vm_name,
            "--port",
            str(port),
            "--priority",
            str(current_priority),
        ]
        success, _ = az_run_command(
            command,
            f"Port '{port}' opened successfully on VM '{vm_name}'.",
            f"Failed to open port '{port}' on VM '{vm_name}'.",
        )
        if not success:
            all_successful = False
            print(f"Error: Not all ports could be opened. Failed on port {port}.")
            # Continue to try other ports or break, depending on desired behavior.
            # For this example, we continue to attempt other ports but record the failure.
        current_priority += 1  # Increment priority for the next rule

    return all_successful


def az_get_vm_public_ip(resource_group: str, vm_name: str) -> str | None:
    """
    Retrieves the public IP address of a VM.

    Args:
        resource_group (str): The name of the resource group.
        vm_name (str): The name of the VM.

    Returns:
        str: The public IP address of the VM, or None if not found.
    """
    print(f"Attempting to retrieve public IP for VM '{vm_name}'...")
    command = [
        "az",
        "vm",
        "show",
        "--resource-group",
        resource_group,
        "--name",
        vm_name,
        "--show-details",
        "--query",
        "publicIps",
        "--output",
        "tsv",
    ]
    success, result_stdout = az_run_command(
        command,
        f"Successfully retrieved public IP for VM '{vm_name}'.",
        f"Failed to retrieve public IP for VM '{vm_name}'.",
    )

    if success and result_stdout:
        ip_address = result_stdout.strip()
        print(f"Found Public IP Address: {ip_address}")
        return ip_address

    return None


# --- Linux commands ---
def linux_run_ssh_command(
    command_parts: list, success_message: str, error_message: str, env=None
) -> bool:
    """
    Executes an SSH command using subprocess.run.

    Args:
        command_parts (list): A list of strings representing the command and its arguments.
        success_message (str): Message to print if the command succeeds.
        error_message (str): Message to print if the command fails.
        env (dict, optional): Environment variables to pass to the subprocess.

    Returns:
        bool: True for success, False for failure.
    """
    try:
        # We don't use check=True here because sshpass might return non-zero for authentication failures
        # which we want to handle gracefully without crashing the script.
        result = subprocess.run(
            command_parts, capture_output=True, text=True, shell=False, env=env
        )

        if result.returncode == 0:
            print(f"Success: {success_message}")
            if result.stdout:
                print(f"STDOUT:\n{result.stdout}")
            return True
        else:
            print(f"Error: {error_message}")
            print(f"Command: {' '.join(command_parts)}")
            print(f"Return Code: {result.returncode}")
            if result.stdout:
                print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")
            return False
    except FileNotFoundError:
        print("Error: sshpass or ssh command not found.")
        print("Please ensure sshpass and ssh are installed and in your system's PATH.")
    except Exception as e:
        print(f"Error: An unexpected error occurred during SSH command: {e}")
    return False


def linux_ssh_to_vm(username: str, password: str, ip_address: str) -> bool:
    """
    Attempts to SSH into the VM and execute commands to print system specs,
    leveraging the SSHPASS environment variable.

    Args:
        username (str): The SSH username.
        password (str): The SSH password.
        ip_address (str): The public IP address of the VM.

    Returns:
        bool: True if SSH connection and command execution is successful, False otherwise.
    """
    print(f"Attempting to SSH into {username}@{ip_address} and print system specs...")

    env_vars = os.environ.copy()
    env_vars["SSHPASS"] = password

    # Commands to get system specifications to check if we can log into VM.
    # We combine them with '&& echo &&' to separate outputs for clarity.
    remote_command = "lscpu && echo && free -h && echo && df -h && echo && uname -a && echo && hostnamectl"

    command = [
        "sshpass",
        "-e",
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        f"{username}@{ip_address}",
        remote_command,  # Execute the remote command
    ]

    success = linux_run_ssh_command(
        command,
        f"Successfully retrieved system specs from VM {ip_address} via SSH.",
        f"Failed to retrieve system specs from VM {ip_address} via SSH.",
        env=env_vars,
    )
    return success


def linux_vm_install_nvidia_drivers(
    username: str, password: str, ip_address: str
) -> bool:
    """
    Attempts to SSH into the VM and execute commands to install NVIDIA drivers
    and initiate a reboot, passing the password directly to sshpass.

    Args:
        username (str): The SSH username.
        password (str): The SSH password.
        ip_address (str): The public IP address of the VM.

    Returns:
        bool: True if driver installation commands are initiated successfully, False otherwise.
              Note: A successful initiation of reboot will likely close the SSH session.
    """
    print(
        f"Attempting to SSH into {username}@{ip_address} to install NVIDIA drivers and reboot..."
    )

    # Combined commands for NVIDIA driver installation
    # The 'sudo reboot' command will terminate the SSH session.
    # We add 'echo "Rebooting..."' to ensure some output before the session drops.
    remote_command = (
        "sudo apt update && sudo apt upgrade -y && "
        "sudo apt install -y build-essential linux-headers-$(uname -r) && "
        "sudo apt update && "
        "sudo apt install -y nvidia-driver-570-server && "
        "sudo update-initramfs -u && "
        "echo 'NVIDIA drivers installed, initiating reboot...' && "
        "sudo reboot"
    )

    command = [
        "sshpass",
        "-p",
        password,  # Pass password directly using -p
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        f"{username}@{ip_address}",
        remote_command,
    ]

    # We expect the SSH session to terminate after reboot, so we handle success carefully.
    success = linux_run_ssh_command(
        command,
        f"NVIDIA driver installation commands sent to VM {ip_address} and reboot initiated.",
        f"Failed to send NVIDIA driver installation commands to VM {ip_address}.",
    )
    # Even if SSH connection drops with an error, if the reboot command was the last one,
    # it might be considered successful initiation.
    # For robust automation, you would typically add a loop here to check VM availability after reboot.
    time.sleep(5)  # give the VM some time to initiate reboot

    return success


def linux_install_cuda_toolkit(username: str, password: str, ip_address: str) -> bool:
    """
    Attempts to SSH into the VM and execute commands to install the NVIDIA CUDA Toolkit.

    Args:
        username (str): The SSH username.
        password (str): The SSH password.
        ip_address (str): The public IP address of the VM.

    Returns:
        bool: True if CUDA Toolkit installation commands are initiated successfully, False otherwise.
    """
    print(
        f"Attempting to SSH into {username}@{ip_address} to install NVIDIA CUDA Toolkit..."
    )

    # Commands for NVIDIA CUDA Toolkit installation
    # Note on `source ~/.bashrc`: This command modifies the current shell's environment variables.
    # When executed via SSH, it only affects the single non-interactive shell session.
    # For changes to persist for future interactive sessions, it's enough, but for immediate use
    # within the same script's SSH commands, it might not directly apply.
    # However, since `nvcc --version` is typically run after a fresh login or after sourcing,
    # and we're installing the toolkit, these steps are included as requested.
    remote_command = (
        "sudo wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb && "
        "sudo apt install -y ./cuda-keyring_1.1-1_all.deb && "
        "sudo apt update && "
        "sudo apt -y install cuda-toolkit-12-8 && "
        "echo 'export PATH=/usr/local/cuda-12.8/bin${PATH:+:${PATH}}' >> ~/.bashrc && "
        "echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.8/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}' >> ~/.bashrc && "
        "source ~/.bashrc && "  # Source bashrc to apply changes for this session
        "echo 'CUDA Toolkit installation complete and environment variables set. You might need to re-login or open a new terminal for changes to fully take effect.'"
    )

    command = [
        "sshpass",
        "-p",
        password,  # Pass password directly using -p
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        f"{username}@{ip_address}",
        remote_command,
    ]

    success = linux_run_ssh_command(
        command,
        f"NVIDIA CUDA Toolkit installation commands sent to VM {ip_address}.",
        f"Failed to send NVIDIA CUDA Toolkit installation commands to VM {ip_address}.",
    )

    return success


def linux_vm_install_docker(username: str, password: str, ip_address: str) -> bool:
    """
    Attempts to SSH into the VM and execute commands to install Docker and Docker Compose.

    Args:
        username (str): The SSH username.
        password (str): The SSH password.
        ip_address (str): The public IP address of the VM.

    Returns:
        bool: True if Docker installation commands are initiated successfully, False otherwise.
    """
    print(f"Attempting to SSH into {username}@{ip_address} to install Docker...")

    # Commands for Docker installation
    # Combined into a single SSH command for efficiency.
    # 'newgrp docker' is for interactive shells; group membership will take effect on next login.
    remote_command = (
        "sudo apt update && "
        "sudo apt install -y apt-transport-https ca-certificates curl software-properties-common && "
        "sudo install -m 0755 -d /etc/apt/keyrings && "
        "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg && "
        "sudo chmod a+r /etc/apt/keyrings/docker.gpg && "
        'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu jammy stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null && '
        "sudo apt update && "
        "sudo apt install -y docker-ce docker-compose-plugin docker-ce-cli containerd.io && "
        "sudo ln -s /usr/libexec/docker/cli-plugins/docker-compose /usr/bin/docker-compose && "
        f"sudo usermod -aG docker {username} && "
        # 'newgrp docker' will not work as expected in non-interactive SSH, but kept as requested
        # "newgrp docker && "
        "sudo systemctl enable docker && "
        "sudo systemctl start docker && "
        "echo 'Docker installation complete. User added to docker group. You might need to re-login for group changes to take full effect.'"
    )

    command = [
        "sshpass",
        "-p",
        password,  # Pass password directly using -p
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        f"{username}@{ip_address}",
        remote_command,
    ]

    success = linux_run_ssh_command(
        command,
        f"Docker installation commands sent to VM {ip_address}.",
        f"Failed to send Docker installation commands to VM {ip_address}.",
    )
    return success


def linux_vm_install_nvidia_container_toolkit(
    username: str, password: str, ip_address: str
) -> bool:
    """
    Attempts to SSH into the VM and execute commands to install the NVIDIA Container Toolkit.

    Args:
        username (str): The SSH username.
        password (str): The SSH password.
        ip_address (str): The public IP address of the VM.

    Returns:
        bool: True if NVIDIA Container Toolkit installation commands are initiated successfully, False otherwise.
    """
    print(
        f"Attempting to SSH into {username}@{ip_address} to install NVIDIA Container Toolkit..."
    )

    remote_command = (
        "curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg && "
        "curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | "
        "sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | "
        "sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list && "
        "sudo apt-get update && "
        "sudo apt-get install -y nvidia-container-toolkit && "
        "sudo nvidia-ctk runtime configure --runtime=docker && "
        "sudo systemctl restart docker && "
        "echo 'NVIDIA Container Toolkit installation complete. Docker restarted.'"
    )

    command = [
        "sshpass",
        "-p",
        password,
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        f"{username}@{ip_address}",
        remote_command,
    ]

    success = linux_run_ssh_command(
        command,
        f"NVIDIA Container Toolkit installation commands sent to VM {ip_address}.",
        f"Failed to send NVIDIA Container Toolkit installation commands to VM {ip_address}.",
    )

    return success

# --- Main execution flow ---
def main() -> None:
    admin_password_try1 = getpass.getpass("Admin password for VM: ")
    admin_password_try2 = getpass.getpass("Enter again: ")
    if admin_password_try1 == admin_password_try2:
        ADMIN_PASSWORD = admin_password_try1
        print("Success: Password is the same.")
    else:
        print("Error: Entered password is not the same.")
        sys.exit(1)

    print("--- Starting Azure VM Provisioning ---")

    # Check and Create Resource Group
    if not az_resource_group_exists(RESOURCE_GROUP_NAME):
        if not az_create_resource_group(RESOURCE_GROUP_NAME, LOCATION):
            print("Aborting: Resource Group creation failed.")
            sys.exit(1)
    else:
        print("Resource Group already exists, skipping creation.")

    # Check and Create Virtual Machine
    if not az_vm_exists(RESOURCE_GROUP_NAME, VM_NAME):
        # The public IP address name is passed directly to the VM create command.
        # The AZ CLI will create the Public IP resource itself.
        if not az_create_vm(
            resource_group=RESOURCE_GROUP_NAME,
            vm_name=VM_NAME,
            image="Ubuntu2404",
            admin_username=ADMIN_USERNAME,
            admin_password=ADMIN_PASSWORD,
            public_ip_sku="Standard",
            public_ip_address_name=f"{VM_NAME}publicip",
            location=LOCATION,
            vm_size=VM_SIZE,
            security_type="TrustedLaunch",
            enable_secure_boot=False,
            enable_vtpm=True,
            os_disk_size_gb=200
        ):
            print("Aborting: Virtual Machine creation failed.")
            sys.exit(1)
    else:
        print("Virtual Machine already exists, skipping creation.")

    # Open ports of VM for public access
    if not az_open_vm_port(RESOURCE_GROUP_NAME, VM_NAME, VM_PUBLIC_PORTS, 100):
        print("Warning: One or more ports could not be opened. VM might not be fully accessible on all desired ports.")
        sys.exit(1)

    # Get the Public IP Address
    vm_public_ip_address = az_get_vm_public_ip(RESOURCE_GROUP_NAME, VM_NAME)

    if not vm_public_ip_address:
        print("\n--- Provisioning Status: Failed to retrieve VM Public IP Address ---")
        print("Please check the Azure portal or CLI for details on the VM's state.")
        sys.exit(1)

    print(f"VM Public IP Address: {vm_public_ip_address}")

    # Attempt to SSH into the VM
    # Note: this is already done per function
    # print("\n--- Attempting SSH Connection ---")
    # if linux_ssh_to_vm(ADMIN_USERNAME, ADMIN_PASSWORD, vm_public_ip_address):
    #    print("Successfully established SSH connection (or sshpass command completed).")
    #    print("Note: The SSH command will typically wait for user interaction.")
    #    print("If you intend to run commands on the VM, modify az_ssh_to_vm to include them.")
    # else:
    #    print("Failed to establish SSH connection.")
    #    exit(1)

    # Install NVIDIA drivers in VM
    if GPU_USED:
        print("\n--- Initiating NVIDIA Driver Installation and VM Reboot ---")
        if linux_vm_install_nvidia_drivers(
            ADMIN_USERNAME, ADMIN_PASSWORD, vm_public_ip_address
        ):
            print(
                "NVIDIA driver installation commands sent. VM is expected to reboot shortly."
            )
        else:
            print(
                "Failed to initiate NVIDIA driver installation. Please check SSH connectivity and VM logs."
            )
            sys.exit(1)

    # Install NVIDIA CUDA Toolkit in VM
    # Note: This is not necessary...
    # print("\n--- Initiating NVIDIA CUDA Toolkit Installation ---")
    # if linux_install_cuda_toolkit(ADMIN_USERNAME, ADMIN_PASSWORD, vm_public_ip_address):
    #     print("NVIDIA CUDA Toolkit installation commands sent successfully.")
    # else:
    #     print("Failed to initiate NVIDIA CUDA Toolkit installation. Please check SSH connectivity and VM logs.")
    #     sys.exit(1)

    # Install Docker in VM
    print("\n--- Initiating Docker Installation ---")
    if linux_vm_install_docker(ADMIN_USERNAME, ADMIN_PASSWORD, vm_public_ip_address):
        print("Docker installation commands sent successfully.")
    else:
        print(
            "Failed to initiate Docker installation. Please check SSH connectivity and VM logs."
        )
        sys.exit(1)

    # Install NVIDIA Container Toolkit in VM
    if not GPU_USED:
        sys.exit(0)

    print("\n--- Initiating NVIDIA Container Toolkit Installation ---")
    if linux_vm_install_nvidia_container_toolkit(
        ADMIN_USERNAME, ADMIN_PASSWORD, vm_public_ip_address
    ):
        print("NVIDIA Container Toolkit installation commands sent successfully.")
    else:
        print(
            "Failed to initiate NVIDIA Container Toolkit installation. Please check SSH connectivity and VM logs."
        )
        sys.exit(1)

    print(
        "Successfully set up NVIDIA T4 VM! Now you can pull and build Docker containers and continue your set up."
    )
    print(f"SSH into this VM via: ssh {ADMIN_USERNAME}@{vm_public_ip_address}")


if __name__ == "__main__":
    main()
