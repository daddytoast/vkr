output "vm_name" {
  description = "VM name in VirtualBox"
  value       = virtualbox_vm.nextcloud.name
}

output "vm_ip" {
  description = "VM IP address (assigned via DHCP on bridged interface)"
  value       = virtualbox_vm.nextcloud.network_adapter[0].ipv4_address
}

output "ansible_inventory_hint" {
  description = "Line to put into ansible/inventory.yml"
  value       = "nextcloud-01 ansible_host=${virtualbox_vm.nextcloud.network_adapter[0].ipv4_address} ansible_user=vagrant"
}