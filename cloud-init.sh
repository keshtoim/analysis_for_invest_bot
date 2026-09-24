#!/bin/bash
# Первичная настройка сервера под бота. Вставляется в поле «Cloud-init» при
# создании сервера (Ubuntu 24.04). Ставит swap + Docker и клонирует проект.
# .env не трогает — там секреты, заполняется вручную после.
#
# Лог выполнения: /var/log/cloud-init-output.log
set -eux

REPO=https://github.com/keshtoim/analysis_for_invest_bot.git
DIR=/opt/analysis_for_invest_bot

# --- swap 2 ГБ: чтобы 1 ГБ RAM хватало на сборку образа ---
if ! swapon --show | grep -q '/swapfile'; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >>/etc/fstab
  echo 'vm.swappiness=10' >/etc/sysctl.d/99-swap.conf
  sysctl -p /etc/sysctl.d/99-swap.conf
fi

# --- Docker + compose ---
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git curl
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# --- проект ---
git clone "$REPO" "$DIR"
cd "$DIR"
cp .env.example .env

cat <<'MSG'

=========================================================
  Docker и проект установлены. Осталось:

    cd /opt/analysis_for_invest_bot
    nano .env          # BOT_TOKEN + AI_PROVIDER и ключ (OPENAI_* или ANTHROPIC_API_KEY)
    docker compose up -d --build
    docker compose logs -f
=========================================================
MSG
