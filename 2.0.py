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
import webbrowser
from urllib.parse import unquote, urlparse
from itertools import zip_longest
from math import ceil
import signal
from tqdm import tqdm
from packaging import version

# Установка титула командной строки
if os.name == 'nt':
    ctypes.windll.kernel32.SetConsoleTitleW("NewZapret | 2.0 | Название обхода: Ожидание... | by Realiz_")

# Отключение предупреждений о неверифицированных SSL-сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================================================
# КОНФИГУРАЦИЯ СИСТЕМЫ
# ================================================
REPO_URL = "https://github.com/bol-van/zapret-win-bundle"
REPO_RAW_URL = "https://raw.githubusercontent.com/bol-van/zapret-win-bundle/master"
UPDATE_REPO = "Realiz-R/NewZapret"
CURRENT_VERSION = "2.0"

BIN_FILES = {
    "WinDivert.dll": f"{REPO_RAW_URL}/zapret-winws/WinDivert.dll",
    "WinDivert64.sys": f"{REPO_RAW_URL}/zapret-winws/WinDivert64.sys",
    "cygwin1.dll": f"{REPO_RAW_URL}/zapret-winws/cygwin1.dll",
    "winws.exe": f"{REPO_RAW_URL}/zapret-winws/winws.exe",
    "quic_initial_www_google_com.bin": "https://github.com/bol-van/zapret/raw/refs/heads/master/files/fake/quic_initial_www_google_com.bin",
    "tls_clienthello_www_google_com.bin": "https://github.com/bol-van/zapret/raw/refs/heads/master/files/fake/tls_clienthello_www_google_com.bin"
}

LIST_FILES = {
    "ipset-all.txt": "https://raw.githubusercontent.com/Realiz-R/NewZapret/refs/heads/main/lists/ipset-all.txt",
    "list-general.txt": "https://raw.githubusercontent.com/Realiz-R/NewZapret/refs/heads/main/lists/list-general.txt",
    "scenarios.json": "https://raw.githubusercontent.com/Realiz-R/NewZapret/refs/heads/main/lists/scenarios.json"
}

REQUIRED_FILES = list(BIN_FILES.keys()) + list(LIST_FILES.keys())
LOG_FILE = "logs/log.txt"
TEST_URLS = [
    "https://discord.com",
    "https://youtube.com",
    "https://cloudflare-ech.com"
]
TEST_TIMEOUT = 10
TEST_ITERATIONS = 2

class ZapretStatus:
    def __init__(self):
        self.reset()
        self.current_scenario = "Ожидание..."
        
    def reset(self):
        self.version = ""
        self.profiles = 0
        self.hostlist = {
            'filename': "",
            'current': 0,
            'updates': [],
            'errors': []
        }
        self.ipset = {
            'filename': "",
            'current': 0,
            'updates': [],
            'errors': []
        }
        self.status = "Инициализация"
        self.last_update = datetime.datetime.now()
        self.message_queue = []

    def set_scenario(self, scenario_name):
        self.current_scenario = scenario_name
        if os.name == 'nt':
            ctypes.windll.kernel32.SetConsoleTitleW(f"NewZapret | 2.0 | Название обхода: {scenario_name} | by Realiz_")

    def parse_line(self, line):
        line = line.strip()
        if not line:
            return

        now = datetime.datetime.now()
        
        if line.startswith('self-built version'):
            self.version = line.replace('self-built version', '').strip()
            self.add_message(f"Обнаружена версия: {self.version}", now)
            return
            
        if 'user defined desync profile' in line:
            parts = line.split()
            self.profiles = int(parts[2])
            self.add_message(f"Загружено профилей: {self.profiles} пользовательских + 1 по умолчанию", now)
            return
            
        if line.startswith('Loading hostlist'):
            filename = line.split()[-1]
            if not self.hostlist['filename']:
                self.hostlist['filename'] = filename
            self.add_message(f"Начало загрузки доменов из {filename}", now)
            return
            
        if line == 'loading plain text list':
            return
            
        if line.startswith('Loaded') and 'hosts from' in line:
            count = int(line.split()[1])
            self.hostlist['current'] = count
            self.hostlist['updates'].append((now, count))
            self.add_message(f"Загружено доменов: {count}", now)
            return
            
        if line.startswith('Loading ipset'):
            filename = line.split()[-1]
            if not self.ipset['filename']:
                self.ipset['filename'] = filename
            self.add_message(f"Начало загрузки IP-адресов из {filename}", now)
            return
            
        if 'bad ip or subnet' in line:
            error_line = line.split(':')[-1].strip()
            self.ipset['errors'].append((now, error_line))
            self.add_message(f"Ошибка в строке {error_line}", now, is_error=True)
            return
            
        if line.startswith('Loaded') and 'ip/subnets from' in line:
            count = int(line.split()[1])
            self.ipset['current'] = count
            self.ipset['updates'].append((now, count))
            self.add_message(f"Загружено IP/подсетей: {count}", now)
            return
            
        if 'windivert initialized' in line:
            self.status = "Активен"
            self.add_message("Система успешно запущена", now)
            return

    def add_message(self, text, timestamp, is_error=False):
        self.message_queue.append({
            'time': timestamp,
            'text': text,
            'error': is_error
        })
        if len(self.message_queue) > 20:
            self.message_queue.pop(0)

    def get_status(self):
        lines = []
        lines.append("╔══════════════════════════════════════════════════╗")
        lines.append("║           СИСТЕМНЫЙ СТАТУС NEWZAPRET            ║")
        lines.append("╚══════════════════════════════════════════════════╝")
        lines.append("")
        lines.append(f"▪ Версия: 2.0 | Сценарий: {self.current_scenario}")
        
        if self.version:
            lines.append(f"▪ Версия ядра: {self.version}")
        
        if self.profiles > 0:
            lines.append(f"▪ Профили обхода: {self.profiles} пользовательских + 1 стандартный")
        
        lines.append(f"▪ Статус: {self.status}")
        lines.append(f"▪ Последнее обновление: {self.last_update.strftime('%H:%M:%S')}")
        lines.append("")
        
        hl = self.hostlist
        status_icon = "✔" if not hl['errors'] else "⚠"
        lines.append(f"{status_icon} СПИСОК ДОМЕНОВ: {hl['filename']}")
        lines.append(f"  ▸ Текущее количество: {hl['current']}")
        
        if hl['updates']:
            lines.append("  ▸ История изменений:")
            for ts, count in hl['updates'][-3:]:
                lines.append(f"    - [{ts.strftime('%H:%M:%S')}] {count} доменов")
        lines.append("")
        
        ips = self.ipset
        status_icon = "✔" if not ips['errors'] else "⚠"
        lines.append(f"{status_icon} СПИСОК IP-АДРЕСОВ: {ips['filename']}")
        lines.append(f"  ▸ Текущее количество: {ips['current']}")
        
        if ips['errors']:
            lines.append("  ▸ Последние ошибки:")
            for ts, err in ips['errors'][-2:]:
                lines.append(f"    - [{ts.strftime('%H:%M:%S')}] Ошибка в строке {err}")
        
        if ips['updates']:
            lines.append("  ▸ История изменений:")
            for ts, count in ips['updates'][-3:]:
                lines.append(f"    - [{ts.strftime('%H:%M:%S')}] {count} IP/подсетей")
        lines.append("")
        
        lines.append("═" * 60)
        lines.append("ПОСЛЕДНИЕ СОБЫТИЯ:")
        for msg in self.message_queue[-5:]:
            prefix = "⚠" if msg['error'] else "▪"
            lines.append(f"{prefix} [{msg['time'].strftime('%H:%M:%S')}] {msg['text']}")
        
        return "\n".join(lines)

def setup_logging():
    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"=== NewZapret log v2.0 - {datetime.datetime.now()} ===\n")

def update_window_title(scenario_name=None):
    title = f"NewZapret | 2.0 | Название обхода: {scenario_name if scenario_name else 'Ожидание...'} | by Realiz_"
    if os.name == 'nt':
        ctypes.windll.kernel32.SetConsoleTitleW(title)

def log_error(message, exception=None):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[ОШИБКА] {datetime.datetime.now()}\n")
        f.write(f"Сообщение: {message}\n")
        if exception:
            f.write(f"Тип ошибки: {type(exception).__name__}\n")
            f.write(f"Подробности: {str(exception)}\n")
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

АВТОМАТИЧЕСКИЙ ОБХОД DPI | ВЕРСИЯ 2.0 | by Realiz_
"""
    print(banner)
    print(f"{'='*60}\n")

def load_scenarios():
    scenarios_file = os.path.join("lists", "scenarios.json")
    if not os.path.exists(scenarios_file):
        return None
    
    try:
        with open(scenarios_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_error("Ошибка загрузки сценариев", e)
        return None

def download_file(url, dest_path):
    try:
        temp_path = dest_path + ".tmp"
        response = requests.get(url, stream=True, timeout=15, verify=False)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        file_exists = os.path.exists(dest_path)
        
        if file_exists:
            try:
                existing_size = os.path.getsize(dest_path)
                if existing_size == total_size:
                    print(f"  ✓ Актуальная версия ({total_size//1024} КБ)")
                    return True
            except OSError:
                existing_size = 0
        
        progress_bar = tqdm(
            total=total_size, 
            unit='B', 
            unit_scale=True,
            desc=f"Загрузка {os.path.basename(dest_path)}",
            leave=False
        )
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    progress_bar.update(len(chunk))
        
        progress_bar.close()
        
        if file_exists:
            os.remove(dest_path)
        os.rename(temp_path, dest_path)
        
        if file_exists:
            print(f"  ✓ Обновлен ({total_size//1024} КБ)")
        else:
            print(f"  ✓ Загружен ({total_size//1024} КБ)")
        
        return True
        
    except Exception as e:
        log_error(f"Ошибка загрузки файла {os.path.basename(dest_path)}", e)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False

def download_newzapret_files():
    print("[1/3] Автоматическое обновление компонентов\n")
    
    os.makedirs("bin", exist_ok=True)
    os.makedirs("lists", exist_ok=True)
    
    success_count = 0
    total_files = len(REQUIRED_FILES)
    
    for i, filename in enumerate(REQUIRED_FILES[:len(BIN_FILES)], 1):
        dest_path = os.path.join("bin", filename)
        raw_url = BIN_FILES[filename]
        
        print(f"[{i}/{total_files}] Обработка {filename}...", end=' ')
        
        if download_file(raw_url, dest_path):
            success_count += 1
    
    for i, filename in enumerate(REQUIRED_FILES[len(BIN_FILES):], len(BIN_FILES) + 1):
        dest_path = os.path.join("lists", filename)
        raw_url = LIST_FILES[filename]
        
        print(f"[{i}/{total_files}] Обработка {filename}...", end=' ')
        
        if download_file(raw_url, dest_path):
            success_count += 1
    
    if success_count == total_files:
        return True
    else:
        log_error(f"Обновлено {success_count}/{total_files} файлов")
        return False

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

def test_scenario(scenario):
    bin_path = os.path.join("bin", "")
    lists_path = os.path.join("lists", "")
    
    args = ["bin\\winws.exe"]
    for arg in scenario['args']:
        formatted_arg = arg.format(
            BIN=bin_path,
            LISTS=lists_path,
            GAME_FILTER="0"
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
        try:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        except:
            pass
    
    return sum(results) / len(results) if results else TEST_TIMEOUT

def auto_select_scenario():
    scenarios = load_scenarios()
    if not scenarios:
        print("Не удалось загрузить сценарии. Использую встроенные.")
        return None
    
    print("\n[3/3] Автоматическое тестирование сценариев\n")
    print(f"Будет протестировано {len(scenarios)} сценариев на {len(TEST_URLS)} сайтах...")
    print("Это займет несколько минут. Пожалуйста, подождите.\n")
    
    results = []
    
    with tqdm(total=len(scenarios)*len(TEST_URLS)*TEST_ITERATIONS, desc="Тестирование сценариев") as pbar:
        for scenario in scenarios:
            try:
                print(f"Тестирование: {scenario['name']}")
                avg_time = test_scenario(scenario)
                results.append((scenario, avg_time))
                pbar.update(len(TEST_URLS)*TEST_ITERATIONS)
                print(f"  ✓ Среднее время: {avg_time:.2f} сек")
            except Exception as e:
                log_error(f"Ошибка тестирования сценария {scenario['name']}", e)
                results.append((scenario, TEST_TIMEOUT * 2))
                pbar.update(len(TEST_URLS)*TEST_ITERATIONS)
    
    results.sort(key=lambda x: x[1])
    
    os.makedirs("logs", exist_ok=True)
    with open("logs/test_results.json", "w", encoding="utf-8") as f:
        json.dump([
            {"scenario": s["name"], "time": t} 
            for s, t in results
        ], f, indent=2, ensure_ascii=False)
    
    print("\nТоп-3 сценариев по скорости:")
    for i, (scenario, avg_time) in enumerate(results[:3]):
        print(f"{i+1}. {scenario['name']}: {avg_time:.2f} сек")
    
    return results[0][0]

def display_scenarios(scenarios):
    if not scenarios:
        print("Нет доступных сценариев")
        return None

    half = ceil(len(scenarios) / 2)
    col1 = scenarios[:half]
    col2 = scenarios[half:]
    
    max_name_len = max(len(s['name']) for s in col1) + 2
    max_id_len = len(str(max(s['id'] for s in scenarios))) + 1
    
    print("\n" + "="*60)
    print("{:^60}".format("ДОСТУПНЫЕ СЦЕНАРИИ ОБХОДА"))
    print("="*60 + "\n")
    
    for left, right in zip_longest(col1, col2, fillvalue=None):
        left_str = f"{left['id']:{max_id_len}}. {left['name']:{max_name_len}}" if left else " "*(max_id_len + max_name_len + 2)
        right_str = f"{right['id']:{max_id_len}}. {right['name']}" if right else ""
        print(left_str + "   " + right_str)
    
    print("\n" + "="*60)
    print("0. Вернуться назад\n")

def select_scenario():
    scenarios = load_scenarios()
    if not scenarios:
        print("Не удалось загрузить сценарии. Использую встроенные.")
        return None
    
    while True:
        display_scenarios(scenarios)
        
        try:
            choice = input("Введите номер сценария: ").strip()
            if choice == "0":
                return None
                
            choice = int(choice)
            for scenario in scenarios:
                if scenario['id'] == choice:
                    return scenario
            print("Неверный номер сценария. Попробуйте снова.")
        except ValueError:
            print("Пожалуйста, введите число.")

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

def run_newzapret(scenario):
    if not scenario:
        print("Ошибка: сценарий не выбран")
        return False
        
    print(f"\nЗапускаю сценарий: {scenario['name']}\n")
    update_window_title(scenario['name'])
    
    missing = []
    for filename in REQUIRED_FILES:
        if not os.path.exists(os.path.join("bin" if filename in BIN_FILES else "lists", filename)):
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
    
    bin_path = os.path.join("bin", "")
    lists_path = os.path.join("lists", "")
    
    args = ["bin\\winws.exe"]
    for arg in scenario['args']:
        formatted_arg = arg.format(
            BIN=bin_path,
            LISTS=lists_path,
            GAME_FILTER="0"
        )
        args.append(formatted_arg)
    
    try:
        clear_screen()
        
        print(r"█▄░█ █▀▀ █░█░█ ▀█ ▄▀█ █▀█ █▀█ █▀▀ ▀█▀")
        print(r"█░▀█ ██▄ ▀▄▀▄▀ █▄ █▀█ █▀▀ █▀▄ ██▄ ░█░")
        print(f"\nСЦЕНАРИЙ: {scenario['name']}")
        print("\nДля завершения работы нажмите любую клавишу...")
        
        process = subprocess.Popen(
            args,
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            universal_newlines=True
        )
        
        zapret_status = ZapretStatus()
        zapret_status.set_scenario(scenario['name'])
        
        def check_key_press():
            while True:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key:
                        try:
                            process.terminate()
                        except:
                            pass
                        return
                time.sleep(0.1)
        
        key_thread = threading.Thread(target=check_key_press, daemon=True)
        key_thread.start()
        
        def signal_handler(sig, frame):
            try:
                process.terminate()
            except:
                pass
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                zapret_status.parse_line(output)
                clear_screen()
                print(zapret_status.get_status())
                print("\nДля завершения работы нажмите любую клавишу...")
        
        return True
        
    except Exception as e:
        error_msg = f"Ошибка запуска: {type(e).__name__}"
        print(f"  ✗ {error_msg}")
        log_error(error_msg, e)
        return False

def check_updates():
    """Проверка наличия обновлений"""
    try:
        print("\nПроверка обновлений...")
        response = requests.get(
            f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10
        )
        response.raise_for_status()
        
        latest_release = response.json()
        latest_version = latest_release['tag_name'].lstrip('v')
        
        if version.parse(latest_version) > version.parse(CURRENT_VERSION):
            print(f"\nДоступна новая версия: v{latest_version} (ваша v{CURRENT_VERSION})")
            print("\nИзменения в новой версии:")
            print(latest_release['body'])
            
            choice = input("\nХотите обновиться? (Y/N): ").strip().lower()
            if choice == 'y' or choice == 'д':
                webbrowser.open(latest_release['html_url'])
                print("Страница загрузки открыта в браузере. После обновления перезапустите программу.")
                time.sleep(3)
                return True
            else:
                print("Обновление отменено. Продолжаем работу с текущей версией.")
                return False
        else:
            print("У вас установлена последняя версия программы.")
            return False
            
    except Exception as e:
        print(f"Ошибка при проверке обновлений: {e}")
        return False

def main():
    try:
        setup_logging()
        update_window_title()
        
        if not is_admin():
            print("Требуются права администратора...")
            time.sleep(1)
            run_as_admin()
            return
        
        print_banner()
        
        # Проверка обновлений при старте
        check_updates()
        
        if not download_newzapret_files():
            print("\n  ⚠ Не все файлы обновлены, работа продолжается")
        
        print("\nВыполняю оптимизацию сети...")
        optimize_network()
        
        while True:
            print("\nВыберите метод выбора сценария:")
            print("1. Автоматический подбор (рекомендуется)")
            print("2. Ручной выбор")
            print("3. Проверить обновления")
            print("0. Выход")
            
            choice = input("\nВаш выбор (0-3): ").strip()
            
            if choice == "0":
                print("\nЗавершение работы...")
                break
            elif choice == "1":
                best_scenario = auto_select_scenario()
                if best_scenario:
                    print(f"\nАвтоматически выбран сценарий: {best_scenario['name']}")
                    run_newzapret(best_scenario)
                else:
                    print("Не удалось выбрать сценарий")
            elif choice == "2":
                scenario = select_scenario()
                if scenario:
                    run_newzapret(scenario)
            elif choice == "3":
                check_updates()
            else:
                print("Неверный выбор. Пожалуйста, введите 0, 1, 2 или 3.")
        
    except KeyboardInterrupt:
        print("\nЗавершение работы по запросу пользователя...")
    except Exception as e:
        error_msg = "Критическая ошибка выполнения"
        print(f"  ✗ {error_msg}")
        log_error(error_msg, e)
        print("\nПодробности в лог-файле")
    finally:
        kill_existing_process()

if __name__ == "__main__":
    main()