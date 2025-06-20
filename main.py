import os
import sys
import ctypes
import requests
import subprocess
import time
import datetime
import traceback
import threading
import msvcrt
import json
import urllib3
from urllib.parse import unquote, urlparse

# Отключение предупреждений о неверифицированных SSL-сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================================================
# КОНФИГУРАЦИЯ СИСТЕМЫ
# ================================================
REPO_URL = "https://github.com/bol-van/zapret-win-bundle"
REPO_RAW_URL = "https://raw.githubusercontent.com/bol-van/zapret-win-bundle/master"

BIN_FILES = {
    "WinDivert.dll": f"{REPO_RAW_URL}/zapret-winws/WinDivert.dll",
    "WinDivert64.sys": f"{REPO_RAW_URL}/zapret-winws/WinDivert64.sys",
    "cygwin1.dll": f"{REPO_RAW_URL}/zapret-winws/cygwin1.dll",
    "winws.exe": f"{REPO_RAW_URL}/zapret-winws/winws.exe",
    "quic_initial_www_google_com.bin": f"{REPO_RAW_URL}/zapret-winws/files/quic_initial_www_google_com.bin",
    "tls_clienthello_www_google_com.bin": "https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/main/bin/tls_clienthello_www_google_com.bin"
}

REQUIRED_FILES = list(BIN_FILES.keys())
LOG_FILE = "logs/log.txt"
TEST_URLS = [
    "https://discord.com",
    "https://youtube.com",
    "https://cloudflare-ech.com"
]
TEST_TIMEOUT = 10
TEST_ITERATIONS = 2

# ================================================
# ПОЛНЫЙ НАБОР СЦЕНАРИЕВ (16 вариантов)
# ================================================
SCENARIOS = [
    {
        "id": 1,
        "name": "⚡ Основной (рекомендуется)",
        "description": "Стандартный сценарий с оптимальным балансом скорости и надежности",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,multidisorder",
            "--dpi-desync-split-pos=midsld",
            "--dpi-desync-repeats=8",
            "--dpi-desync-fooling=md5sig,badseq",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,multidisorder",
            "--dpi-desync-split-pos=midsld",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fooling=md5sig,badseq",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=10",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n2"
        ],
        "requires_tls": False
    },
    {
        "id": 2,
        "name": "🚀 Альтернативный (ALT)",
        "description": "Альтернативная конфигурация для улучшенной скорости",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split",
            "--dpi-desync-autottl=5",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fooling=badseq",
            "--dpi-desync-fake-tls={BIN}tls_clienthello_www_google_com.bin",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split",
            "--dpi-desync-autottl=5",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fooling=badseq",
            "--dpi-desync-fake-tls={BIN}tls_clienthello_www_google_com.bin",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=12",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n3"
        ],
        "requires_tls": True
    },
    {
        "id": 3,
        "name": "🔧 Альтернативный 2 (ALT2)",
        "description": "Вторая альтернативная конфигурация с оптимизацией",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=split2",
            "--dpi-desync-split-seqovl=652",
            "--dpi-desync-split-pos=2",
            "--dpi-desync-split-seqovl-pattern={BIN}tls_clienthello_www_google_com.bin",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=split2",
            "--dpi-desync-split-seqovl=652",
            "--dpi-desync-split-pos=2",
            "--dpi-desync-split-seqovl-pattern={BIN}tls_clienthello_www_google_com.bin",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=12",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n2"
        ],
        "requires_tls": True
    },
    {
        "id": 4,
        "name": "🛠️ Альтернативный 3 (ALT3)",
        "description": "Третья альтернативная конфигурация",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=split",
            "--dpi-desync-split-pos=1",
            "--dpi-desync-autottl",
            "--dpi-desync-fooling=badseq",
            "--dpi-desync-repeats=8",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=split",
            "--dpi-desync-split-pos=1",
            "--dpi-desync-autottl",
            "--dpi-desync-fooling=badseq",
            "--dpi-desync-repeats=8",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=10",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n2"
        ],
        "requires_tls": False
    },
    {
        "id": 5,
        "name": "🔩 Альтернативный 4 (ALT4)",
        "description": "Четвертая альтернативная конфигурация",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fooling=md5sig",
            "--dpi-desync-fake-tls={BIN}tls_clienthello_www_google_com.bin",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fooling=md5sig",
            "--dpi-desync-fake-tls={BIN}tls_clienthello_www_google_com.bin",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=10",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n2"
        ],
        "requires_tls": True
    },
    {
        "id": 6,
        "name": "⚙️ Альтернативный 5 (ALT5)",
        "description": "Пятая альтернативная конфигурация",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-l3=ipv4",
            "--filter-tcp=443,{GAME_FILTER}",
            "--dpi-desync=syndata",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=14",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n3"
        ],
        "requires_tls": False
    },
    {
        "id": 7,
        "name": "🔒 Альтернативный 6 (ALT6)",
        "description": "Шестая альтернативная конфигурация",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=split2",
            "--dpi-desync-repeats=2",
            "--dpi-desync-split-seqovl=681",
            "--dpi-desync-split-pos=1",
            "--dpi-desync-fooling=badseq,hopbyhop2",
            "--dpi-desync-split-seqovl-pattern={BIN}tls_clienthello_www_google_com.bin",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=split2",
            "--dpi-desync-split-seqovl=681",
            "--dpi-desync-split-pos=1",
            "--dpi-desync-fooling=badseq,hopbyhop2",
            "--dpi-desync-split-seqovl-pattern={BIN}tls_clienthello_www_google_com.bin",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=12",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n2"
        ],
        "requires_tls": True
    },
    {
        "id": 8,
        "name": "🛡️ Фейковый TLS (FAKE TLS ALT)",
        "description": "Использует фейковый TLS для обхода DPI",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-fooling=md5sig",
            "--dpi-desync-fake-tls-mod=rnd,rndsni,padencap",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-fooling=md5sig",
            "--dpi-desync-fake-tls-mod=rnd,rndsni,padencap",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=10",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n2"
        ],
        "requires_tls": True
    },
    {
        "id": 9,
        "name": "🔓 Фейковый TLS Авто (FAKE TLS AUTO ALT)",
        "description": "Автоматическая настройка фейкового TLS",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=11",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,fakedsplit",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=split",
            "--dpi-desync-split-pos=1",
            "--dpi-desync-autottl",
            "--dpi-desync-fooling=badseq",
            "--dpi-desync-repeats=8",
            "--dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=11",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,fakedsplit",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=split",
            "--dpi-desync-split-pos=1",
            "--dpi-desync-autottl",
            "--dpi-desync-fooling=badseq",
            "--dpi-desync-repeats=8",
            "--dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=10",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n2"
        ],
        "requires_tls": True
    },
    {
        "id": 10,
        "name": "💡 Фейковый TLS Авто 2 (FAKE TLS AUTO ALT2)",
        "description": "Улучшенная автоматическая настройка фейкового TLS",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=11",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,fakedsplit",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-split-seqovl=681",
            "--dpi-desync-split-pos=1",
            "--dpi-desync-fooling=badseq",
            "--dpi-desync-repeats=8",
            "--dpi-desync-split-seqovl-pattern={BIN}tls_clienthello_www_google_com.bin",
            "--dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=11",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,fakedsplit",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-split-seqovl=681",
            "--dpi-desync-split-pos=1",
            "--dpi-desync-fooling=badseq",
            "--dpi-desync-repeats=8",
            "--dpi-desync-split-seqovl-pattern={BIN}tls_clienthello_www_google_com.bin",
            "--dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=10",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n2"
        ],
        "requires_tls": True
    },
    {
        "id": 11,
        "name": "🔐 Фейковый TLS Авто (FAKE TLS AUTO)",
        "description": "Оптимизированная автоматическая настройка TLS",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=11",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,fakedsplit",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,multidisorder",
            "--dpi-desync-split-pos=1,midsld",
            "--dpi-desync-repeats=11",
            "--dpi-desync-fooling=md5sig",
            "--dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=11",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,fakedsplit",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,multidisorder",
            "--dpi-desync-split-pos=1,midsld",
            "--dpi-desync-repeats=11",
            "--dpi-desync-fooling=md5sig",
            "--dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=10",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n2"
        ],
        "requires_tls": True
    },
    {
        "id": 12,
        "name": "🖥️ Фейковый TLS (FAKE TLS)",
        "description": "Стандартная настройка фейкового TLS",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=8",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=3",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-ttl=4",
            "--dpi-desync-fake-tls-mod=rnd,rndsni,padencap",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=8",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=3",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-ttl=4",
            "--dpi-desync-fake-tls-mod=rnd,rndsni,padencap",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=12",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n3"
        ],
        "requires_tls": True
    },
    {
        "id": 13,
        "name": "🏢 МГТС (Оптимизированный)",
        "description": "Оптимизирован для сетей МГТС",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fooling=badseq",
            "--dpi-desync-fake-tls={BIN}tls_clienthello_www_google_com.bin",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fooling=badseq",
            "--dpi-desync-fake-tls={BIN}tls_clienthello_www_google_com.bin",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=10",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n2"
        ],
        "requires_tls": True
    },
    {
        "id": 14,
        "name": "🏢 МГТС 2 (Оптимизированный)",
        "description": "Вторая оптимизированная версия для МГТС",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fooling=md5sig",
            "--dpi-desync-fake-tls={BIN}tls_clienthello_www_google_com.bin",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fooling=md5sig",
            "--dpi-desync-fake-tls={BIN}tls_clienthello_www_google_com.bin",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=12",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n3"
        ],
        "requires_tls": True
    },
    {
        "id": 15,
        "name": "🌐 QUIC+HTTP/3 Обход (Кастомный)",
        "description": "Комбинированный обход через QUIC с фрагментацией и мультиплексированием",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=8",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-http3=1",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=3",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=multiplex",
            "--dpi-desync-quic=1",
            "--dpi-desync-http3=1",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=8",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=3",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=multiplex",
            "--dpi-desync-quic=1",
            "--dpi-desync-http3=1",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=3",
            "--dpi-desync-repeats=12",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n3"
        ],
        "requires_tls": True
    },
    {
        "id": 16,
        "name": "🌀 TTL+Чередование (Кастомный)",
        "description": "Динамическое чередование TTL с фрагментацией и изменением порядка пакетов",
        "args": [
            "--wf-tcp=80,443,{GAME_FILTER}",
            "--wf-udp=443,50000-50100,{GAME_FILTER}",
            "--filter-udp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-udp=50000-50100",
            "--filter-l7=discord,stun",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--new",
            "--filter-tcp=80",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443",
            "--hostlist={LISTS}list-general.txt",
            "--dpi-desync=ttl-alternate",
            "--dpi-desync-ttl-min=32",
            "--dpi-desync-ttl-max=128",
            "--dpi-desync-split-min=64",
            "--dpi-desync-split-max=512",
            "--dpi-desync-reorder=1",
            "--dpi-desync-repeats=8",
            "--new",
            "--filter-udp=443",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-repeats=6",
            "--dpi-desync-fake-quic={BIN}quic_initial_www_google_com.bin",
            "--new",
            "--filter-tcp=80",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake,split2",
            "--dpi-desync-autottl=2",
            "--dpi-desync-fooling=md5sig",
            "--new",
            "--filter-tcp=443,{GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=ttl-alternate",
            "--dpi-desync-ttl-min=32",
            "--dpi-desync-ttl-max=128",
            "--dpi-desync-split-min=64",
            "--dpi-desync-split-max=512",
            "--dpi-desync-reorder=1",
            "--dpi-desync-repeats=8",
            "--new",
            "--filter-udp={GAME_FILTER}",
            "--ipset={LISTS}ipset-all.txt",
            "--dpi-desync=fake",
            "--dpi-desync-autottl=2",
            "--dpi-desync-repeats=12",
            "--dpi-desync-any-protocol=1",
            "--dpi-desync-fake-unknown-udp={BIN}quic_initial_www_google_com.bin",
            "--dpi-desync-cutoff=n3"
        ],
        "requires_tls": False
    }
]

# ================================================
# СИСТЕМНЫЕ УТИЛИТЫ
# ================================================
def setup_logging():
    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== nozaprets log v1.1 - {datetime.datetime.now()} ===\n")

def log_error(message, exception=None):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[ОШИБКА] {datetime.datetime.now()}\n")
        f.write(f"Сообщение: {message}\n")
        if exception:
            f.write(f"Исключение: {str(exception)}\n")
            f.write(f"Трассировка:\n{traceback.format_exc()}\n")
        f.write("-"*50 + "\n")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        log_error("Ошибка проверки прав администратора", e)
        return False

def run_as_admin():
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
    except Exception as e:
        log_error("Ошибка запроса прав администратора", e)
        print("Не удалось запросить права администратора")
        time.sleep(2)
        sys.exit(1)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    clear_screen()
    banner = r"""
█▄░█ █▀▀ █░█░█ ▀█ ▄▀█ █▀█ █▀█ █▀▀ ▀█▀
█░▀█ ██▄ ▀▄▀▄▀ █▄ █▀█ █▀▀ █▀▄ ██▄ ░█░

АВТОМАТИЧЕСКИЙ ОБХОД DPI | ВЕРСИЯ 1.1
"""
    print(banner)
    print(f"{'='*60}\n")

# ================================================
# УЛУЧШЕННАЯ ЗАГРУЗКА ФАЙЛОВ
# ================================================
def download_file(url, dest_path):
    try:
        temp_path = dest_path + ".tmp"
        response = requests.get(url, stream=True, timeout=15, verify=False)
        response.raise_for_status()
        
        file_exists = os.path.exists(dest_path)
        if file_exists:
            try:
                existing_size = os.path.getsize(dest_path)
            except OSError:
                existing_size = 0
        else:
            existing_size = 0
            
        new_size = int(response.headers.get('content-length', 0))
        
        if file_exists and existing_size == new_size:
            print(f"  ✓ Актуальная версия ({new_size//1024} КБ)")
            return True
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        if file_exists:
            os.remove(dest_path)
        os.rename(temp_path, dest_path)
        
        if file_exists:
            print(f"  ✓ Обновлен ({new_size//1024} КБ)")
        else:
            print(f"  ✓ Загружен ({new_size//1024} КБ)")
        
        return True
        
    except Exception as e:
        log_error(f"Ошибка загрузки файла {os.path.basename(dest_path)}", e)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False

def download_nozaprets_files():
    print("[1/3] Автоматическое обновление компонентов\n")
    
    os.makedirs("bin", exist_ok=True)
    os.makedirs("lists", exist_ok=True)
    
    success_count = 0
    total_files = len(REQUIRED_FILES)
    
    for i, filename in enumerate(REQUIRED_FILES, 1):
        dest_path = os.path.join("bin", filename)
        raw_url = BIN_FILES[filename]
        
        print(f"[{i}/{total_files}] Обработка {filename}...", end=' ')
        
        if download_file(raw_url, dest_path):
            success_count += 1
    
    if success_count == total_files:
        return True
    else:
        log_error(f"Обновлено {success_count}/{total_files} файлов")
        return False

# ================================================
# ОПТИМИЗАЦИЯ СЕТЕВЫХ ПАРАМЕТРОВ
# ================================================
def optimize_network():
    print("\n[2/3] Оптимизация сетевых параметров\n")
    
    optimizations = [
        ("Настройка автонастройки TCP", 'netsh int tcp set global autotuninglevel=experimental'),
        ("Активация масштабирования окна TCP", 'netsh int tcp set global rss=enabled'),
        ("Включение кэширующей обработки", 'netsh int tcp set global chimney=enabled'),
        ("Активация аппаратного ускорения", 'netsh int tcp set global dca=enabled'),
        ("Оптимизация ECN", 'netsh int tcp set global ecncapability=enabled'),
        ("Настройка обработки перегрузок", 'netsh int tcp set global congestionprovider=ctcp'),
        ("Оптимизация размера TCP-окна", 'netsh int tcp set global initialRto=1000'),
    ]
    
    success_count = 0
    
    for desc, cmd in optimizations:
        print(f"{desc}...", end=' ')
        try:
            result = subprocess.run(
                cmd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("Успешно")
                success_count += 1
            else:
                print("Не поддерживается")
                log_error(f"Оптимизация не поддерживается: {desc}")
        except Exception as e:
            print("Ошибка выполнения")
            log_error(f"Ошибка выполнения оптимизации: {desc}", e)
    
    return success_count >= 4

# ================================================
# ТЕСТИРОВАНИЕ СЦЕНАРИЕВ
# ================================================
def test_scenario(scenario):
    game_filter = "1024-65535" if os.path.exists("game_filter.enabled") else "0"
    bin_path = os.path.join("bin", "")
    lists_path = os.path.join("lists", "")
    
    args = ["bin\\winws.exe"]
    for arg in scenario['args']:
        formatted_arg = arg.format(
            BIN=bin_path,
            LISTS=lists_path,
            GAME_FILTER=game_filter
        )
        args.append(formatted_arg)
    
    process = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.getcwd()
    )
    
    time.sleep(3)
    
    results = []
    session = requests.Session()
    session.verify = False
    
    try:
        for url in TEST_URLS:
            url_times = []
            for _ in range(TEST_ITERATIONS):
                try:
                    start_time = time.time()
                    response = session.head(url, timeout=TEST_TIMEOUT, allow_redirects=True)
                    response.raise_for_status()
                    elapsed = time.time() - start_time
                    url_times.append(elapsed)
                except Exception as e:
                    url_times.append(TEST_TIMEOUT)
                    log_error(f"Ошибка теста {url} для сценария {scenario['name']}", e)
            
            results.append(min(url_times))
    
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    
    return sum(results) / len(results) if results else TEST_TIMEOUT

def auto_select_scenario():
    print("\n[3/3] Автоматическое тестирование сценариев\n")
    print(f"Будет протестировано {len(SCENARIOS)} сценариев на {len(TEST_URLS)} сайтах...")
    print("Это займет несколько минут. Пожалуйста, подождите.\n")
    
    results = []
    
    for scenario in SCENARIOS:
        try:
            print(f"Тестирование: {scenario['name']}...")
            avg_time = test_scenario(scenario)
            results.append((scenario, avg_time))
            print(f"  ✓ Среднее время: {avg_time:.2f} сек")
        except Exception as e:
            log_error(f"Ошибка тестирования сценария {scenario['name']}", e)
            results.append((scenario, TEST_TIMEOUT * 2))
    
    results.sort(key=lambda x: x[1])
    
    with open("logs/test_results.json", "w", encoding="utf-8") as f:
        json.dump([
            {"scenario": s["name"], "time": t} 
            for s, t in results
        ], f, indent=2, ensure_ascii=False)
    
    print("\nТоп-3 сценариев по скорости:")
    for i, (scenario, avg_time) in enumerate(results[:3]):
        print(f"{i+1}. {scenario['name']}: {avg_time:.2f} сек")
    
    return results[0][0]

def select_scenario():
    print("\n[3/3] Выбор сценария обхода\n")
    print("Доступные сценарии:")
    
    for scenario in SCENARIOS:
        print(f"\n{scenario['id']}. {scenario['name']}")
        print(f"   {scenario['description']}")
    
    print("\n" + "="*60)
    
    while True:
        try:
            choice = int(input("\nВведите номер сценария: "))
            for scenario in SCENARIOS:
                if scenario['id'] == choice:
                    return scenario
            print("Неверный номер сценария. Попробуйте снова.")
        except ValueError:
            print("Пожалуйста, введите число.")

# ================================================
# ЗАПУСК СИСТЕМЫ
# ================================================
def kill_existing_process():
    try:
        result = subprocess.run(
            'tasklist /FI "IMAGENAME eq winws.exe"',
            shell=True,
            capture_output=True,
            text=True,
            encoding='cp866',
            errors='ignore'
        )
        
        if "winws.exe" in result.stdout:
            print("Обнаружен работающий процесс, завершаю...")
            subprocess.run('taskkill /F /IM winws.exe', shell=True, check=True)
            time.sleep(1)
            return True
        return False
    except Exception as e:
        log_error("Ошибка завершения процесса", e)
        return False

def run_nozaprets(scenario):
    print(f"\nЗапускаю сценарий: {scenario['name']}\n")
    
    missing = []
    for filename in REQUIRED_FILES:
        if not os.path.exists(os.path.join("bin", filename)):
            missing.append(filename)
    
    if scenario.get('requires_tls', False):
        tls_file = os.path.join("bin", "tls_clienthello_www_google_com.bin")
        if not os.path.exists(tls_file):
            print(f"\n  ⚠ Внимание! Для этого сценария требуется файл {tls_file}")
            print("  Скачайте его вручную или выберите другой сценарий")
            return False
    
    if missing:
        error_msg = "Отсутствуют необходимые файлы: " + ", ".join(missing)
        print(f"  ✗ {error_msg}")
        log_error(error_msg)
        return False
    
    kill_existing_process()
    
    game_filter = "1024-65535" if os.path.exists("game_filter.enabled") else "0"
    
    bin_path = os.path.join("bin", "")
    lists_path = os.path.join("lists", "")
    
    args = ["bin\\winws.exe"]
    for arg in scenario['args']:
        formatted_arg = arg.format(
            BIN=bin_path,
            LISTS=lists_path,
            GAME_FILTER=game_filter
        )
        args.append(formatted_arg)
    
    try:
        clear_screen()
        
        print(r"█▄░█ █▀▀ █░█░█ ▀█ ▄▀█ █▀█ █▀█ █▀▀ ▀█▀")
        print(r"█░▀█ ██▄ ▀▄▀▄▀ █▄ █▀█ █▀▀ █▀▄ ██▄ ░█░")
        print(f"\nСЦЕНАРИЙ: {scenario['name']}")
        print("\nДля завершения работы нажмите любую клавишу\n")
        
        process = subprocess.Popen(
            args,
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        def check_key_press():
            while True:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key:
                        process.terminate()
                        return
                time.sleep(0.1)
        
        key_thread = threading.Thread(target=check_key_press, daemon=True)
        key_thread.start()
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        return True
        
    except Exception as e:
        error_msg = f"Ошибка запуска: {type(e).__name__}"
        print(f"  ✗ {error_msg}")
        log_error(error_msg, e)
        return False

# ================================================
# ГЛАВНЫЙ СКРИПТ
# ================================================
def main():
    try:
        setup_logging()
        
        if not is_admin():
            print("Требуются права администратора...")
            time.sleep(1)
            run_as_admin()
            return
        
        print_banner()
        
        if not download_nozaprets_files():
            print("\n  ⚠ Не все файлы обновлены, работа продолжается")
        
        print("\nВыполняю оптимизацию сети...")
        optimize_network()
        
        print("\nВыберите метод выбора сценария:")
        print("1. Автоматический подбор (рекомендуется)")
        print("2. Ручной выбор")
        
        while True:
            choice = input("\nВведите номер варианта (1-2): ").strip()
            if choice == "1":
                best_scenario = auto_select_scenario()
                print(f"\nАвтоматически выбран сценарий: {best_scenario['name']}")
                run_nozaprets(best_scenario)
                break
            elif choice == "2":
                scenario = select_scenario()
                run_nozaprets(scenario)
                break
            else:
                print("Неверный выбор. Пожалуйста, введите 1 или 2.")
        
    except Exception as e:
        error_msg = "Критическая ошибка выполнения"
        print(f"  ✗ {error_msg}")
        log_error(error_msg, e)
        print("\nПодробности в лог-файле")

if __name__ == "__main__":
    main()