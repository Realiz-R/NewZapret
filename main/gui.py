import os
import sys
import ctypes
import requests
import subprocess
import time
import datetime
import traceback
import threading
import json
import urllib3
from urllib.parse import unquote, urlparse
import flet as ft

# Отключение предупреждений о неверифицированных SSL-сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Конфигурация системы (остается без изменений)
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

class NewZapretApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.setup_page()
        self.setup_state()
        self.setup_ui()
        
    def setup_page(self):
        self.page.title = "NewZapret GUI"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.vertical_alignment = ft.MainAxisAlignment.START
        self.page.padding = 20
        self.page.window_width = 900
        self.page.window_height = 700
        
    def setup_state(self):
        self.is_running = False
        self.current_scenario = None
        self.process = None
        self.scenarios = []
        
    def setup_ui(self):
        # Создаем элементы интерфейса
        self.status_indicator = ft.Icon(name=ft.icons.CIRCLE, color=ft.colors.RED)
        self.scenario_dropdown = ft.Dropdown(options=[], hint_text="Выберите сценарий", expand=True)
        self.log_view = ft.ListView(expand=True)
        self.progress_bar = ft.ProgressBar(width=400, visible=False)
        
        self.test_results_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Сценарий")),
                ft.DataColumn(ft.Text("Среднее время (сек)")),
                ft.DataColumn(ft.Text("Статус"))
            ],
            rows=[]
        )
        
        # Собираем интерфейс
        header = ft.Row(
            controls=[
                ft.Icon(ft.icons.SECURITY, size=30),
                ft.Text("NewZapret", size=24, weight=ft.FontWeight.BOLD)
            ],
            alignment=ft.MainAxisAlignment.CENTER
        )
        
        status_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Текущий статус:", size=16),
                    ft.Row([self.status_indicator, ft.Text("Не активно", expand=True)]),
                    ft.Row([
                        self.scenario_dropdown,
                        ft.ElevatedButton(
                            "Запустить",
                            icon=ft.icons.PLAY_ARROW,
                            on_click=self.start_scenario,
                            disabled=True
                        ),
                        ft.ElevatedButton(
                            "Остановить",
                            icon=ft.icons.STOP,
                            on_click=self.stop_scenario,
                            disabled=True
                        )
                    ])
                ], spacing=10),
                padding=15
            )
        )
        
        actions_row = ft.Row([
            ft.ElevatedButton(
                "Обновить компоненты",
                icon=ft.icons.UPDATE,
                on_click=self.update_components
            ),
            ft.ElevatedButton(
                "Оптимизировать сеть",
                icon=ft.icons.TUNE,
                on_click=self.optimize_network
            ),
            ft.ElevatedButton(
                "Тестировать сценарии",
                icon=ft.icons.SPEED,
                on_click=self.test_scenarios
            )
        ], spacing=10)
        
        # Добавляем все элементы на страницу
        self.page.add(
            header,
            status_card,
            actions_row,
            ft.Text("Прогресс:", visible=False),
            self.progress_bar,
            ft.Text("Результаты тестирования:", weight=ft.FontWeight.BOLD),
            ft.Container(
                content=self.test_results_table,
                border=ft.border.all(1),
                padding=10,
                height=200
            ),
            ft.Text("Лог событий:", weight=ft.FontWeight.BOLD),
            ft.Container(
                content=self.log_view,
                border=ft.border.all(1),
                padding=10,
                height=200,
                expand=True
            )
        )
        
        self.load_scenarios()
        
    def log_message(self, message, is_error=False):
        """Добавляет сообщение в лог"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = ft.Text(f"[{timestamp}] {message}", color=ft.colors.RED if is_error else None)
        self.log_view.controls.append(log_entry)
        self.page.update()
        
        # Сохраняем в файл лога
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def load_scenarios(self):
        """Загружает сценарии из файла"""
        try:
            scenarios_file = os.path.join("lists", "scenarios.json")
            if not os.path.exists(scenarios_file):
                self.log_message("Файл сценариев не найден", is_error=True)
                return
            
            with open(scenarios_file, "r", encoding="utf-8") as f:
                self.scenarios = json.load(f)
                
            self.scenario_dropdown.options = [
                ft.dropdown.Option(
                    key=str(scenario["id"]),
                    text=scenario["name"]
                ) for scenario in self.scenarios
            ]
            
            # Активируем кнопку запуска если есть сценарии
            if self.scenarios:
                for control in self.page.controls:
                    if isinstance(control, ft.ElevatedButton) and control.text == "Запустить":
                        control.disabled = False
            
            self.page.update()
            self.log_message(f"Загружено {len(self.scenarios)} сценариев")
            
        except Exception as e:
            self.log_message(f"Ошибка загрузки сценариев: {str(e)}", is_error=True)
    
    def update_components(self, e):
        """Обновляет компоненты системы"""
        self.progress_bar.visible = True
        self.page.update()
        
        self.log_message("Начинаю обновление компонентов...")
        
        os.makedirs("bin", exist_ok=True)
        os.makedirs("lists", exist_ok=True)
        
        success_count = 0
        
        # Загрузка бинарных файлов
        for filename in BIN_FILES:
            dest_path = os.path.join("bin", filename)
            raw_url = BIN_FILES[filename]
            
            self.log_message(f"Загрузка {filename}...")
            
            if self.download_file(raw_url, dest_path):
                success_count += 1
        
        # Загрузка файлов списков
        for filename in LIST_FILES:
            dest_path = os.path.join("lists", filename)
            raw_url = LIST_FILES[filename]
            
            self.log_message(f"Загрузка {filename}...")
            
            if self.download_file(raw_url, dest_path):
                success_count += 1
        
        self.progress_bar.visible = False
        self.page.update()
        
        if success_count == len(REQUIRED_FILES):
            self.log_message("Все компоненты успешно обновлены!")
        else:
            self.log_message(f"Обновлено {success_count}/{len(REQUIRED_FILES)} файлов", is_error=True)
    
    def download_file(self, url, dest_path):
        """Загружает файл с URL"""
        try:
            temp_path = dest_path + ".tmp"
            response = requests.get(url, stream=True, timeout=15, verify=False)
            response.raise_for_status()
            
            file_exists = os.path.exists(dest_path)
            if file_exists:
                existing_size = os.path.getsize(dest_path)
            else:
                existing_size = 0
                
            new_size = int(response.headers.get('content-length', 0))
            
            if file_exists and existing_size == new_size:
                self.log_message(f"  {os.path.basename(dest_path)} уже актуален")
                return True
            
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            if file_exists:
                os.remove(dest_path)
            os.rename(temp_path, dest_path)
            
            self.log_message(f"  {os.path.basename(dest_path)} успешно {'обновлен' if file_exists else 'загружен'}")
            return True
            
        except Exception as e:
            self.log_message(f"Ошибка загрузки файла {os.path.basename(dest_path)}: {str(e)}", is_error=True)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            return False
    
    def optimize_network(self, e):
        """Оптимизирует сетевые параметры"""
        self.log_message("Начинаю оптимизацию сети...")
        
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
                    self.log_message(f"{desc} - успешно")
                    success_count += 1
                else:
                    self.log_message(f"{desc} - не поддерживается")
            except Exception as e:
                self.log_message(f"Ошибка выполнения {desc}: {str(e)}", is_error=True)
        
        if success_count >= 4:
            self.log_message("Оптимизация сети завершена успешно!")
        else:
            self.log_message("Оптимизация сети завершена с ограничениями", is_error=True)
    
    def test_scenarios(self, e):
        """Тестирует все сценарии"""
        if not self.scenarios:
            self.log_message("Нет доступных сценариев для тестирования", is_error=True)
            return
        
        self.test_results_table.rows = []
        self.progress_bar.visible = True
        self.page.update()
        
        self.log_message(f"Начинаю тестирование {len(self.scenarios)} сценариев...")
        
        results = []
        
        for scenario in self.scenarios:
            try:
                self.log_message(f"Тестирование: {scenario['name']}...")
                avg_time = self.test_scenario(scenario)
                results.append((scenario, avg_time))
                
                self.test_results_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(scenario["name"])),
                        ft.DataCell(ft.Text(f"{avg_time:.2f}")),
                        ft.DataCell(ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN))
                    ])
                )
                self.page.update()
                
                self.log_message(f"  {scenario['name']}: среднее время {avg_time:.2f} сек")
            except Exception as e:
                self.log_message(f"Ошибка тестирования сценария {scenario['name']}: {str(e)}", is_error=True)
                results.append((scenario, TEST_TIMEOUT * 2))
        
        results.sort(key=lambda x: x[1])
        
        self.progress_bar.visible = False
        self.page.update()
        
        self.log_message("Тестирование завершено!")
        
        # Автоматически выбираем лучший сценарий
        if results:
            best_scenario = results[0][0]
            self.scenario_dropdown.value = str(best_scenario["id"])
            self.page.update()
            self.log_message(f"Рекомендуемый сценарий: {best_scenario['name']}")
    
    def test_scenario(self, scenario):
        """Тестирует один сценарий"""
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
                        self.log_message(f"Ошибка теста {url}: {str(e)}", is_error=True)
                
                results.append(min(url_times))
        
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        
        return sum(results) / len(results) if results else TEST_TIMEOUT
    
    def start_scenario(self, e):
        """Запускает выбранный сценарий"""
        if not self.scenario_dropdown.value:
            self.log_message("Не выбран сценарий для запуска", is_error=True)
            return
        
        scenario_id = int(self.scenario_dropdown.value)
        self.current_scenario = next((s for s in self.scenarios if s["id"] == scenario_id), None)
        
        if not self.current_scenario:
            self.log_message("Выбранный сценарий не найден", is_error=True)
            return
        
        self.log_message(f"Запускаю сценарий: {self.current_scenario['name']}")
        
        # Проверка необходимых файлов
        missing = []
        for filename in REQUIRED_FILES:
            if not os.path.exists(os.path.join("bin" if filename in BIN_FILES else "lists", filename)):
                missing.append(filename)
        
        if missing:
            self.log_message(f"Отсутствуют необходимые файлы: {', '.join(missing)}", is_error=True)
            return
        
        # Проверка TLS файла если требуется
        if self.current_scenario.get('requires_tls', False):
            tls_file = os.path.join("bin", "tls_clienthello_www_google_com.bin")
            if not os.path.exists(tls_file):
                self.log_message(f"Для этого сценария требуется файл {tls_file}", is_error=True)
                return
        
        # Завершаем предыдущий процесс если есть
        self.kill_existing_process()
        
        # Запускаем новый процесс
        bin_path = os.path.join("bin", "")
        lists_path = os.path.join("lists", "")
        
        args = ["bin\\winws.exe"]
        for arg in self.current_scenario['args']:
            formatted_arg = arg.format(
                BIN=bin_path,
                LISTS=lists_path,
                GAME_FILTER="0"
            )
            args.append(formatted_arg)
        
        try:
            self.process = subprocess.Popen(
                args,
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            self.is_running = True
            self.status_indicator.color = ft.colors.GREEN
            self.status_indicator.name = ft.icons.CIRCLE
            
            # Обновляем кнопки
            for control in self.page.controls:
                if isinstance(control, ft.ElevatedButton):
                    if control.text == "Запустить":
                        control.disabled = True
                    elif control.text == "Остановить":
                        control.disabled = False
            
            self.page.update()
            self.log_message("Сценарий успешно запущен!")
            
            # Поток для чтения вывода
            def read_output():
                while self.is_running and self.process.poll() is None:
                    line = self.process.stdout.readline()
                    if line:
                        self.log_message(line.strip())
            
            threading.Thread(target=read_output, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"Ошибка запуска сценария: {str(e)}", is_error=True)
    
    def stop_scenario(self, e):
        """Останавливает текущий сценарий"""
        if not self.is_running:
            return
        
        self.log_message("Останавливаю текущий сценарий...")
        self.is_running = False
        
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        
        self.status_indicator.color = ft.colors.RED
        self.status_indicator.name = ft.icons.CIRCLE
        
        # Обновляем кнопки
        for control in self.page.controls:
            if isinstance(control, ft.ElevatedButton):
                if control.text == "Запустить":
                    control.disabled = False
                elif control.text == "Остановить":
                    control.disabled = True
        
        self.page.update()
        self.log_message("Сценарий остановлен")
    
    def kill_existing_process(self):
        """Завершает работающий процесс winws.exe"""
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
                self.log_message("Обнаружен работающий процесс, завершаю...")
                subprocess.run('taskkill /F /IM winws.exe', shell=True, check=True)
                time.sleep(1)
                return True
            return False
        except Exception as e:
            self.log_message(f"Ошибка завершения процесса: {str(e)}", is_error=True)
            return False

def main(page: ft.Page):
    # Проверка прав администратора
    try:
        if not ctypes.windll.shell32.IsUserAnAdmin():
            page.dialog = ft.AlertDialog(
                title=ft.Text("Требуются права администратора"),
                content=ft.Text("Пожалуйста, запустите приложение от имени администратора"),
                on_dismiss=lambda e: sys.exit()
            )
            page.update()
            return
    except:
        pass
    
    # Создаем папку для логов если ее нет
    os.makedirs("logs", exist_ok=True)
    
    # Инициализируем приложение
    app = NewZapretApp(page)

if __name__ == "__main__":
    ft.app(target=main)