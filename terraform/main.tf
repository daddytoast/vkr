terraform {
  required_version = ">= 1.6.0"

  required_providers {
    virtualbox = {
      source  = "terra-farm/virtualbox"
      version = "0.2.2-alpha.1"
    }
  }
}

provider "virtualbox" {}

resource "virtualbox_vm" "nextcloud" {
  name   = var.vm_name
  image  = var.vm_image
  cpus   = var.vm_cores
  memory = "${var.vm_memory} mib"

  network_adapter {
    type           = "bridged"
    host_interface = var.host_network_interface
  }
}

# После apply получить IP: VBoxManage guestproperty get <vm-name> /VirtualBox/GuestInfo/Net/0/V4/IP
# Или из terraform output, потом вписать в ansible/inventory.yml