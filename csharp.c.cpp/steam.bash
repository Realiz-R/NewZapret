#!/bin/bash
DOMAINS=("store.steampowered.com" "steamcommunity.com" "api.steampowered.com")
IPSET_NAME="steam_set"

# Создать набор (если не существует)
sudo ipset create $IPSET_NAME hash:ip 2>/dev/null

# Очистить старые IP
sudo ipset flush $IPSET_NAME

# Добавить текущие IP
for domain in "${DOMAINS[@]}"; do
  ips=$(dig +short $domain A | grep -E '^[0-9\.]+$')
  for ip in $ips; do
    sudo ipset add $IPSET_NAME $ip 2>/dev/null
  done
done