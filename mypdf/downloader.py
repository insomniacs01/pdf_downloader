#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from urllib.parse import urlparse, unquote
from datetime import datetime
import threading
import requests
from playwright.sync_api import sync_playwright
import random
import queue


class PDFDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("批量PDF下载器 v6.0")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)

        self.setup_styles()
        self.is_downloading = False
        self.stop_event = threading.Event()
        self.config_file = 'config.json'
        self.load_config()
        self.create_widgets()
        self.session = self.create_session()
        self.download_queue = queue.Queue()
        self.current_task_index = 0

    def setup_styles(self):
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')

        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        style.configure('Info.TLabel', foreground='blue')
        style.configure('Warning.TLabel', foreground='orange')

    def create_session(self):
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.get_random_user_agent(),
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })
        return session

    def get_random_user_agent(self):
        agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        ]
        return random.choice(agents)

    def load_config(self):
        self.config = {
            'save_path': os.path.join(os.getcwd(), 'downloads'),
            'wait_time': 3,
            'page_size': 'A4',
            'landscape': False,
            'scale': 1.0,
            'print_background': True,
            'block_images': False,
            'remove_popups': True,
            'full_load': True,
            'scroll_pause': 2,
            'max_scroll_time': 60
        }

        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config.update(json.load(f))
        except:
            pass

    def save_config(self):
        try:
            self.config.update({
                'save_path': self.save_path_var.get(),
                'wait_time': self.wait_time_var.get(),
                'page_size': self.page_size_var.get(),
                'landscape': self.landscape_var.get(),
                'scale': self.scale_var.get(),
                'print_background': self.print_bg_var.get(),
                'block_images': self.block_images_var.get(),
                'remove_popups': self.remove_popups_var.get(),
                'full_load': self.full_load_var.get(),
                'scroll_pause': self.scroll_pause_var.get(),
                'max_scroll_time': self.max_scroll_var.get()
            })

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except:
            pass

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        ttk.Label(main_frame, text="批量PDF下载器", style='Title.TLabel').grid(row=0, column=0, pady=(0, 20))

        paned = ttk.PanedWindow(main_frame, orient='horizontal')
        paned.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        main_frame.rowconfigure(1, weight=1)

        left_frame = ttk.Frame(paned)
        right_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        paned.add(right_frame, weight=2)

        url_frame = ttk.LabelFrame(left_frame, text="下载地址（每行一个）", padding="10")
        url_frame.pack(fill='both', expand=True, padx=(0, 5))

        url_button_frame = ttk.Frame(url_frame)
        url_button_frame.pack(fill='x', pady=(0, 10))

        ttk.Button(url_button_frame, text="粘贴", command=self.paste_urls).pack(side='left', padx=(0, 5))
        ttk.Button(url_button_frame, text="导入文件", command=self.import_urls).pack(side='left', padx=5)
        ttk.Button(url_button_frame, text="清空", command=self.clear_urls).pack(side='left', padx=5)

        url_text_frame = ttk.Frame(url_frame)
        url_text_frame.pack(fill='both', expand=True)

        self.url_text = tk.Text(url_text_frame, height=15, wrap='none', font=('Consolas', 10))
        self.url_text.pack(side='left', fill='both', expand=True)

        url_scrollbar_y = ttk.Scrollbar(url_text_frame, orient='vertical', command=self.url_text.yview)
        url_scrollbar_y.pack(side='right', fill='y')
        self.url_text.configure(yscrollcommand=url_scrollbar_y.set)

        url_scrollbar_x = ttk.Scrollbar(url_frame, orient='horizontal', command=self.url_text.xview)
        url_scrollbar_x.pack(fill='x')
        self.url_text.configure(xscrollcommand=url_scrollbar_x.set)

        self.url_count_label = ttk.Label(url_frame, text="共 0 个链接")
        self.url_count_label.pack(pady=(10, 0))

        self.url_text.bind('<KeyRelease>', self.update_url_count)

        task_frame = ttk.LabelFrame(right_frame, text="任务列表", padding="10")
        task_frame.pack(fill='both', expand=True, padx=(5, 0))

        columns = ('序号', '地址', '状态', '进度', '文件名')
        self.task_tree = ttk.Treeview(task_frame, columns=columns, show='headings', height=15)

        self.task_tree.heading('序号', text='序号')
        self.task_tree.heading('地址', text='地址')
        self.task_tree.heading('状态', text='状态')
        self.task_tree.heading('进度', text='进度')
        self.task_tree.heading('文件名', text='文件名')

        self.task_tree.column('序号', width=50)
        self.task_tree.column('地址', width=300)
        self.task_tree.column('状态', width=80)
        self.task_tree.column('进度', width=80)
        self.task_tree.column('文件名', width=200)

        tree_scrollbar = ttk.Scrollbar(task_frame, orient='vertical', command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=tree_scrollbar.set)

        self.task_tree.pack(side='left', fill='both', expand=True)
        tree_scrollbar.pack(side='right', fill='y')

        self.task_tree.tag_configure('pending', foreground='gray')
        self.task_tree.tag_configure('downloading', foreground='blue')
        self.task_tree.tag_configure('success', foreground='green')
        self.task_tree.tag_configure('error', foreground='red')

        settings_frame = ttk.LabelFrame(main_frame, text="设置", padding="10")
        settings_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)

        ttk.Label(settings_frame, text="保存位置:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.save_path_var = tk.StringVar(value=self.config['save_path'])
        ttk.Entry(settings_frame, textvariable=self.save_path_var).grid(row=0, column=1, sticky=(tk.W, tk.E),
                                                                        padx=(0, 10))
        ttk.Button(settings_frame, text="浏览", command=self.browse_folder).grid(row=0, column=2)

        page_frame = ttk.Frame(settings_frame)
        page_frame.grid(row=1, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E))

        ttk.Label(page_frame, text="页面大小:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.page_size_var = tk.StringVar(value=self.config['page_size'])
        ttk.Combobox(page_frame, textvariable=self.page_size_var,
                     values=['A4', 'A3', 'A5', 'Letter', 'Legal'],
                     state='readonly', width=10).grid(row=0, column=1, padx=(0, 20))

        self.landscape_var = tk.BooleanVar(value=self.config['landscape'])
        ttk.Checkbutton(page_frame, text="横向", variable=self.landscape_var).grid(row=0, column=2, padx=(0, 20))

        ttk.Label(page_frame, text="初始等待(秒):").grid(row=0, column=3, padx=(0, 10))
        self.wait_time_var = tk.IntVar(value=self.config['wait_time'])
        ttk.Spinbox(page_frame, from_=0, to=30, textvariable=self.wait_time_var, width=8).grid(row=0, column=4)

        options_frame = ttk.Frame(settings_frame)
        options_frame.grid(row=2, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E))

        self.print_bg_var = tk.BooleanVar(value=self.config['print_background'])
        self.block_images_var = tk.BooleanVar(value=self.config['block_images'])
        self.remove_popups_var = tk.BooleanVar(value=self.config['remove_popups'])
        self.full_load_var = tk.BooleanVar(value=self.config.get('full_load', True))

        ttk.Checkbutton(options_frame, text="打印背景", variable=self.print_bg_var).grid(row=0, column=0, padx=(0, 20))
        ttk.Checkbutton(options_frame, text="屏蔽图片", variable=self.block_images_var).grid(row=0, column=1,
                                                                                             padx=(0, 20))
        ttk.Checkbutton(options_frame, text="移除弹窗", variable=self.remove_popups_var).grid(row=0, column=2,
                                                                                              padx=(0, 20))
        ttk.Checkbutton(options_frame, text="完整加载", variable=self.full_load_var).grid(row=0, column=3)

        scroll_frame = ttk.Frame(settings_frame)
        scroll_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E))

        ttk.Label(scroll_frame, text="滚动停顿(秒):").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.scroll_pause_var = tk.IntVar(value=self.config.get('scroll_pause', 2))
        ttk.Spinbox(scroll_frame, from_=1, to=10, textvariable=self.scroll_pause_var, width=8).grid(row=0, column=1,
                                                                                                    padx=(0, 20))

        ttk.Label(scroll_frame, text="最大滚动时间(秒):").grid(row=0, column=2, padx=(0, 10))
        self.max_scroll_var = tk.IntVar(value=self.config.get('max_scroll_time', 60))
        ttk.Spinbox(scroll_frame, from_=10, to=300, textvariable=self.max_scroll_var, width=8, increment=10).grid(row=0,
                                                                                                                  column=3)

        scale_frame = ttk.Frame(settings_frame)
        scale_frame.grid(row=4, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E))

        ttk.Label(scale_frame, text="缩放:").grid(row=0, column=0, sticky='w', padx=(0, 10))
        self.scale_var = tk.DoubleVar(value=self.config['scale'])
        scale_scale = ttk.Scale(scale_frame, from_=0.5, to=2.0, orient='horizontal',
                                variable=self.scale_var, length=200)
        scale_scale.grid(row=0, column=1, padx=(0, 10))

        self.scale_label = ttk.Label(scale_frame, text=f"{self.scale_var.get():.1f}")
        self.scale_label.grid(row=0, column=2)
        scale_scale.config(command=lambda v: self.scale_label.config(text=f"{float(v):.1f}"))

        progress_frame = ttk.LabelFrame(main_frame, text="总体进度", padding="10")
        progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)

        self.overall_progress_var = tk.DoubleVar()
        self.overall_progress_bar = ttk.Progressbar(progress_frame, variable=self.overall_progress_var, maximum=100)
        self.overall_progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.status_label = ttk.Label(progress_frame, text="就绪", style='Success.TLabel')
        self.status_label.grid(row=1, column=0)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        self.download_btn = ttk.Button(button_frame, text="开始下载", command=self.start_download)
        self.download_btn.grid(row=0, column=0, padx=(0, 10))

        self.stop_btn = ttk.Button(button_frame, text="停止", command=self.stop_download, state='disabled')
        self.stop_btn.grid(row=0, column=1, padx=(0, 10))

        ttk.Button(button_frame, text="打开文件夹", command=self.open_folder).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(button_frame, text="清空任务", command=self.clear_tasks).grid(row=0, column=3)

    def update_url_count(self, event=None):
        urls = self.get_urls()
        self.url_count_label.config(text=f"共 {len(urls)} 个链接")

    def get_urls(self):
        text = self.url_text.get(1.0, tk.END).strip()
        if not text:
            return []
        return [url.strip() for url in text.split('\n') if url.strip()]

    def paste_urls(self):
        try:
            clipboard_text = self.root.clipboard_get().strip()
            current_text = self.url_text.get(1.0, tk.END).strip()
            if current_text:
                self.url_text.insert(tk.END, '\n' + clipboard_text)
            else:
                self.url_text.insert(1.0, clipboard_text)
            self.update_url_count()
        except:
            pass

    def import_urls(self):
        file_path = filedialog.askopenfilename(
            title="选择URL文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    urls = f.read().strip()
                    current_text = self.url_text.get(1.0, tk.END).strip()
                    if current_text:
                        self.url_text.insert(tk.END, '\n' + urls)
                    else:
                        self.url_text.insert(1.0, urls)
                    self.update_url_count()
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {str(e)}")

    def clear_urls(self):
        self.url_text.delete(1.0, tk.END)
        self.update_url_count()

    def clear_tasks(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_path_var.get())
        if folder:
            self.save_path_var.set(folder)

    def open_folder(self):
        path = self.save_path_var.get()
        if os.path.exists(path):
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')

    def is_pdf_url(self, url):
        try:
            if url.lower().endswith('.pdf'):
                return True
            response = self.session.head(url, timeout=5, allow_redirects=True)
            return 'application/pdf' in response.headers.get('Content-Type', '').lower()
        except:
            return False

    def get_filename_from_url(self, url, is_pdf=True):
        parsed = urlparse(url)
        filename = os.path.basename(unquote(parsed.path))

        if not is_pdf:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"webpage_{timestamp}.pdf"
        elif not filename or not filename.endswith('.pdf'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"download_{timestamp}.pdf"

        return filename

    def update_task_status(self, item_id, status, progress='', filename=''):
        tag = 'pending'
        if status == '下载中':
            tag = 'downloading'
        elif status == '完成':
            tag = 'success'
        elif '失败' in status or '错误' in status:
            tag = 'error'

        values = list(self.task_tree.item(item_id, 'values'))
        values[2] = status
        if progress:
            values[3] = progress
        if filename:
            values[4] = filename

        self.task_tree.item(item_id, values=values, tags=(tag,))
        self.task_tree.see(item_id)

    def download_pdf_direct(self, url, filepath, item_id):
        try:
            self.update_task_status(item_id, '下载中')
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.stop_event.is_set():
                        self.update_task_status(item_id, '已停止')
                        return False

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self.update_task_status(item_id, '下载中', f"{progress:.1f}%")

            self.update_task_status(item_id, '完成', '100%', os.path.basename(filepath))
            return True
        except Exception as e:
            self.update_task_status(item_id, f'失败: {str(e)}')
            return False

    def convert_webpage_to_pdf(self, url, filepath, item_id):
        try:
            self.update_task_status(item_id, '启动浏览器')

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-setuid-sandbox',
                        '--disable-accelerated-2d-canvas',
                        '--disable-gpu'
                    ]
                )

                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent=self.get_random_user_agent(),
                    bypass_csp=True,
                    ignore_https_errors=True,
                    locale='zh-CN',
                    storage_state={
                        'cookies': [
                            {
                                'name': 'CONSENT',
                                'value': 'YES+',
                                'domain': '.kaggle.com',
                                'path': '/'
                            },
                            {
                                'name': 'kaggle_cookie_consent',
                                'value': 'accepted',
                                'domain': '.kaggle.com',
                                'path': '/'
                            }
                        ]
                    }
                )

                page = context.new_page()
                page.set_default_timeout(60000)

                if self.block_images_var.get():
                    page.route("**/*.{png,jpg,jpeg,gif,webp,svg}", lambda route: route.abort())

                self.update_task_status(item_id, '加载页面')

                page.goto(url, wait_until='domcontentloaded', timeout=45000)

                if self.remove_popups_var.get():
                    try:
                        page.wait_for_timeout(1000)
                        cookie_selectors = [
                            'button:has-text("OK, Got it")',
                            'button:has-text("Accept")',
                            'button:has-text("Accept all")',
                            'button:has-text("I agree")',
                            'button:has-text("同意")',
                            '[aria-label*="accept"]',
                            '[aria-label*="Accept"]'
                        ]

                        for selector in cookie_selectors:
                            try:
                                btn = page.query_selector(selector)
                                if btn and btn.is_visible():
                                    btn.click()
                                    page.wait_for_timeout(500)
                                    break
                            except:
                                continue
                    except:
                        pass

                page.wait_for_load_state('load', timeout=30000)

                wait_time = self.wait_time_var.get()
                if wait_time > 0:
                    self.update_task_status(item_id, f'等待{wait_time}秒')
                    for i in range(wait_time):
                        if self.stop_event.is_set():
                            browser.close()
                            return None
                        time.sleep(1)

                if self.remove_popups_var.get():
                    page.evaluate("""
                        () => {
                            const selectors = [
                                '.modal', '.popup', '.overlay', '.dialog', 
                                '[class*="modal"]', '[class*="popup"]', '[role="dialog"]',
                                '[class*="cookie"]', '[class*="consent"]', '[class*="gdpr"]',
                                '.alert', '.banner', '.notification',
                                'div[style*="position: fixed"]', 'div[style*="position:fixed"]'
                            ];

                            selectors.forEach(s => {
                                document.querySelectorAll(s).forEach(el => {
                                    const style = getComputedStyle(el);
                                    if (style.zIndex > 100 || style.position === 'fixed') {
                                        el.remove();
                                    }
                                });
                            });

                            document.body.style.overflow = '';
                            document.documentElement.style.overflow = '';
                            document.body.classList.remove('modal-open', 'no-scroll');
                        }
                    """)

                if self.full_load_var.get():
                    self.update_task_status(item_id, '加载内容')

                    page.evaluate("""
                        () => {
                            const lazySelectors = [
                                'img[data-src]', 'img[data-lazy]', 'img[data-original]',
                                'img.lazy', 'img.lazyload', '[data-background-image]',
                                'img[loading="lazy"]', 'img[data-lazy-src]'
                            ];

                            lazySelectors.forEach(selector => {
                                document.querySelectorAll(selector).forEach(img => {
                                    if (img.dataset.src) img.src = img.dataset.src;
                                    if (img.dataset.lazySrc) img.src = img.dataset.lazySrc;
                                    if (img.dataset.original) img.src = img.dataset.original;
                                    if (img.dataset.backgroundImage) {
                                        img.style.backgroundImage = `url(${img.dataset.backgroundImage})`;
                                    }
                                    img.removeAttribute('loading');
                                });
                            });

                            window.dispatchEvent(new Event('scroll'));
                            window.dispatchEvent(new Event('resize'));
                        }
                    """)

                    self.update_task_status(item_id, '滚动加载')
                    scroll_pause = self.scroll_pause_var.get() * 1000
                    max_scroll_time = self.max_scroll_var.get()
                    start_scroll_time = time.time()

                    last_height = 0
                    no_change_count = 0

                    while True:
                        if self.stop_event.is_set():
                            browser.close()
                            return None

                        current_height = page.evaluate("document.body.scrollHeight")

                        if current_height == last_height:
                            no_change_count += 1
                            if no_change_count >= 3:
                                break
                        else:
                            no_change_count = 0

                        last_height = current_height

                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(scroll_pause)

                        elapsed = time.time() - start_scroll_time
                        if elapsed > max_scroll_time:
                            break

                    page.evaluate("window.scrollTo(0, 0)")
                    page.wait_for_timeout(1000)

                self.update_task_status(item_id, '生成PDF')

                try:
                    title = page.title()
                    if title:
                        import re
                        title = re.sub(r'[<>:"/\\|?*]', '', title).strip()[:50]
                        if title:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filepath = os.path.join(os.path.dirname(filepath), f"{title}_{timestamp}.pdf")
                except:
                    pass

                page.pdf(
                    path=filepath,
                    format=self.page_size_var.get(),
                    landscape=self.landscape_var.get(),
                    print_background=self.print_bg_var.get(),
                    scale=self.scale_var.get(),
                    margin={'top': '1cm', 'bottom': '1cm', 'left': '1cm', 'right': '1cm'},
                    prefer_css_page_size=True
                )

                browser.close()

                self.update_task_status(item_id, '完成', '100%', os.path.basename(filepath))
                return filepath

        except Exception as e:
            self.update_task_status(item_id, f'失败: {str(e)}')
            return None

    def stop_download(self):
        self.stop_event.set()
        self.status_label.config(text="正在停止...", style='Warning.TLabel')

    def start_download(self):
        if self.is_downloading:
            messagebox.showwarning("警告", "已有下载任务进行中！")
            return

        urls = self.get_urls()
        if not urls:
            messagebox.showerror("错误", "请输入下载地址！")
            return

        self.save_config()

        save_path = self.save_path_var.get()
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        self.clear_tasks()

        for i, url in enumerate(urls):
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            item_id = self.task_tree.insert('', 'end', values=(i + 1, url, '等待中', '', ''), tags=('pending',))
            self.download_queue.put((url, item_id))

        self.is_downloading = True
        self.stop_event.clear()
        self.download_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.overall_progress_var.set(0)
        self.current_task_index = 0

        thread = threading.Thread(target=self._download_worker)
        thread.daemon = True
        thread.start()

    def _download_worker(self):
        total_tasks = self.download_queue.qsize()
        completed_tasks = 0

        try:
            while not self.download_queue.empty():
                if self.stop_event.is_set():
                    break

                url, item_id = self.download_queue.get()
                self.current_task_index += 1

                self.root.after(0, lambda: self.status_label.config(
                    text=f"下载中 ({self.current_task_index}/{total_tasks})",
                    style='Info.TLabel'
                ))

                save_path = self.save_path_var.get()
                is_pdf = self.is_pdf_url(url)
                filename = self.get_filename_from_url(url, is_pdf)
                filepath = os.path.join(save_path, filename)

                counter = 1
                base_name = os.path.splitext(filename)[0]
                ext = os.path.splitext(filename)[1]
                while os.path.exists(filepath):
                    filename = f"{base_name}_{counter}{ext}"
                    filepath = os.path.join(save_path, filename)
                    counter += 1

                if is_pdf:
                    success = self.download_pdf_direct(url, filepath, item_id)
                else:
                    result = self.convert_webpage_to_pdf(url, filepath, item_id)
                    success = result is not None

                if success:
                    completed_tasks += 1

                progress = (self.current_task_index / total_tasks) * 100
                self.root.after(0, lambda p=progress: self.overall_progress_var.set(p))

            if self.stop_event.is_set():
                final_text = f"已停止 (完成 {completed_tasks}/{total_tasks})"
                style = 'Warning.TLabel'
            else:
                final_text = f"全部完成 ({completed_tasks}/{total_tasks})"
                style = 'Success.TLabel'

            self.root.after(0, lambda: self.status_label.config(text=final_text, style=style))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
        finally:
            self.root.after(0, lambda: (
                setattr(self, 'is_downloading', False),
                self.download_btn.config(state='normal'),
                self.stop_btn.config(state='disabled')
            ))


def main():
    try:
        import requests
        import playwright
    except ImportError:
        print("请安装依赖: pip install requests playwright")
        print("然后运行: python -m playwright install chromium")
        return

    root = tk.Tk()
    app = PDFDownloaderGUI(root)

    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f'{w}x{h}+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    main()