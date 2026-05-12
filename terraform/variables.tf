variable "vm_name" {
  description = "VM name"
  type        = string
  default     = "nextcloud"
}

variable "vm_image" {
  description = "Ubuntu 22.04 Vagrant box (.box file URL or local path)"
  type        = string
  # Official Ubuntu 22.04 LTS box with VirtualBox Guest Additions
  default     = "https://app.vagrantup.com/ubuntu/boxes/jammy64/versions/20230616.0.0/providers/virtualbox.box"
}

variable "vm_cores" {
  description = "Number of vCPUs"
  type        = number
  default     = 2
}

variable "vm_memory" {
  description = "RAM in MiB"
  type        = number
  default     = 4096
}

variable "host_network_interface" {
  description = "Host NIC name for bridged networking (run: VBoxManage list bridgedifs)"
  type        = string
  # Linux example: "enp3s0"   Windows example: "Intel(R) Ethernet Connection"
  default     = "enp3s0"
}