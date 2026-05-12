https://github.com/daddytoast/vkr
https://github.com/daddytoast/vkr
https://github.com/daddytoast/vkr



# Безопасная инфраструктура КФС на основе IaC

ВКР — Разработка безопасной инфраструктуры для киберфизической системы  
на основе управления и описания инфраструктуры через конфигурационные файлы.

## Архитектура
┌─────────────────────────────────────────────────────┐
│ Физический мир │
│ MikroTik hAP ax³ ── DHCP leases ── кто в сети │
└────────────────────────┬────────────────────────────┘
│ RouterOS REST API
┌────────────────────────▼────────────────────────────┐
│ КФС — Python сервис                                 │
│ collector/mikrotik_client.py → SQLite               |  
│ dashboard/app.py → Flask + SSE                      │
└────────────────────────┬────────────────────────────┘
│ HTTP / SSE
┌────────────────────────▼────────────────────────────┐
│ Dashboard (браузер)                                 │
│ Количество людей · Список устройств · График        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ IaC — инфраструктура                                │
│ Terraform → VirtualBox VM → Ubuntu 22.04            │
│ Ansible → Docker + Nextcloud + Nginx + MariaDB      │
└─────────────────────────────────────────────────────┘

## Структура репозитория
.
├── terraform/ # Провизионирование VM в VirtualBox
│ ├── main.tf
│ ├── variables.tf
│ ├── outputs.tf
│ └── terraform.tfvars.example
│
├── ansible/ # Настройка Nextcloud через Docker
│ ├── ansible.cfg
│ ├── inventory.yml
│ ├── playbook.yml
│ ├── group_vars/all.yml
│ └── roles/nextcloud/
│ ├── tasks/ # system, docker, firewall, nextcloud, ssl
│ ├── handlers/
│ ├── templates/ # docker-compose.yml.j2, nginx.conf.j2
│ └── defaults/
│
└── cps/ # Киберфизическая часть
├── collector/
│ ├── mikrotik_client.py # RouterOS REST API клиент
│ └── database.py # SQLite хранилище
├── dashboard/
│ ├── app.py # Flask + SSE
│ ├── templates/index.html
│ └── static/style.css
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── config.yml.example

## Быстрый старт
### 1. Инфраструктура (Terraform + Ansible)
```bash
# Узнать имя сетевого интерфейса хоста
VBoxManage list bridgedifs | grep "^Name:"
# Создать VM в VirtualBox
cd terraform
cp terraform.tfvars.example terraform.tfvars
# вписать host_network_interface из команды выше
terraform init
terraform apply
# Получить IP виртуальной машины
terraform output vm_ip
# Вписать этот IP в ansible/inventory.yml → ansible_host
# Настроить Nextcloud
cd ../ansible
# зашифровать секреты: ansible-vault encrypt_string 'password' --name 'var'
ansible-playbook playbook.yml --ask-vault-pass
2. КФС Dashboard
cd cps
cp config.yml.example config.yml
# заполнить config.yml: адрес MikroTik, логин/пароль API

# Запуск через Docker
docker compose up -d

# Или напрямую
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python dashboard/app.py
Открыть браузер: http://localhost:8080

Создание API-пользователя в RouterOS
/user/group/add name=api-ro policy=read,api
/user/add name=api-user group=api-ro password=api-password
Безопасность
Компонент	Меры
Terraform	Секреты только в terraform.tfvars 
Ansible	Пароли в Ansible Vault, не в открытом виде
Nextcloud	HTTPS (TLS 1.2/1.3), HSTS, fail2ban, UFW
MikroTik	Read-only API-пользователь, HTTPS REST API
Dashboard	Без аутентификации по умолчанию — разверните за reverse proxy с Basic Auth
