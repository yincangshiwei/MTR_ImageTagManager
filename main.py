import os
import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog
from PIL import Image, ImageTk, ImageOps
from ttkbootstrap import Style
from tkinter.scrolledtext import ScrolledText
import threading
import requests
import random
import configparser
import time
from hashlib import md5
from pathlib import Path


class ImageTagManager:
    def __init__(self, root):
        self.root = root
        self.style = Style(theme='cosmo')
        self.style.configure('TFrame', background='#f5f5f5')
        self.style.configure('Selected.TFrame', background='#a8dadc')
        self.style.configure('TButton', padding=5)
        self.style.configure('TEntry', padding=5)
        self.root.title("图像标签管理工具")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        # 配置变量
        self.baidu_appid = ""
        self.baidu_token = ""
        self.target_language = "zh"
        self.grid_cols = 4  # 默认宫格列数
        # 历史目录列表
        self.history_dirs = []
        # 数据存储
        self.image_dir = ""
        self.image_files = []
        self.current_image_index = None
        self.tag_data = {}
        self.view_mode = "grid"
        self.thumb_size = (180, 180)
        # 缓存优化
        self.thumb_cache = {}  # 缩略图缓存
        self.preview_cache = {}  # 预览图缓存
        # 创建界面
        self.create_menu()
        self.create_main_pane()
        self.create_left_panel()
        self.create_right_panel()
        self.create_status_bar()
        # 初始化布局比例
        self.root.update_idletasks()
        self.root.after(100, self.set_initial_sash)
        # 配置文件管理
        self.config_path = Path(__file__).parent / "config.ini"
        self.load_config()
        self.update_history_menu()
        # 定期清理缓存
        self.root.after(60000, self.clear_old_cache)  # 每分钟清理一次

    # 缓存清理方法
    def clear_old_cache(self):
        now = time.time()
        for key in list(self.thumb_cache.keys()):
            if now - self.thumb_cache[key]['timestamp'] > 3600:
                del self.thumb_cache[key]
        for key in list(self.preview_cache.keys()):
            if now - self.preview_cache[key]['timestamp'] > 3600:
                del self.preview_cache[key]
        self.root.after(60000, self.clear_old_cache)

    # 缩略图加载
    def load_thumbnail(self, img_path, size=(180, 180)):
        if img_path in self.thumb_cache:
            return self.thumb_cache[img_path]['image']
        try:
            img = Image.open(img_path)
            img = ImageOps.contain(img, size)
            photo = ImageTk.PhotoImage(img)
            self.thumb_cache[img_path] = {'image': photo, 'timestamp': time.time()}
            return photo
        except:
            return None

    # 预览图加载
    def load_preview(self, img_path, max_size=(800, 600)):
        if img_path in self.preview_cache:
            return self.preview_cache[img_path]['image']
        try:
            img = Image.open(img_path)
            img.thumbnail(max_size)
            photo = ImageTk.PhotoImage(img)
            self.preview_cache[img_path] = {'image': photo, 'timestamp': time.time()}
            return photo
        except:
            return None

    # 异步化翻译方法
    def translate_api_async(self, query, to_lang, callback):
        def worker():
            result = self.translate_api(query, to_lang)
            self.root.after(0, callback, result)

        threading.Thread(target=worker, daemon=True).start()

    # 目录加载方法
    def load_directory(self, directory=None):
        if directory is None:
            directory = filedialog.askdirectory()
        if not directory:
            return
        self.show_progress()
        # 更新历史记录
        if directory in self.history_dirs:
            self.history_dirs.remove(directory)
        self.history_dirs.insert(0, directory)
        self.history_dirs = self.history_dirs[:5]
        self.image_dir = directory
        self.image_files = [
            f for f in os.listdir(self.image_dir)
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        self.tag_data = {}
        for img in self.image_files:
            tag_file = os.path.splitext(img)[0] + ".txt"
            try:
                with open(os.path.join(self.image_dir, tag_file), 'r', encoding='utf-8') as f:
                    self.tag_data[img] = f.read().strip()
            except FileNotFoundError:
                self.tag_data[img] = ""
        if self.image_files:
            if self.view_mode == "grid":
                self.show_grid_view()
            else:
                self.show_list_view()
            self.update_status(f"加载完成：{len(self.image_files)}张图片")
        else:
            self.update_status("未找到有效图片文件")
        self.root.after(500, self.hide_progress)
        self.save_all_config()
        self.update_history_menu()

    # 宫格视图
    def show_grid_view(self):
        self.clear_view()
        for idx, img_file in enumerate(self.image_files):
            row, col = divmod(idx, self.grid_cols)
            frame = ttk.Frame(self.scrollable_frame, style='TFrame', padding=5)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
            self.create_image_card(frame, img_file, idx)

    # 列表视图
    def show_list_view(self):
        self.clear_view()
        for idx, img_file in enumerate(self.image_files):
            frame = ttk.Frame(self.scrollable_frame, style='TFrame', padding=5)
            frame.pack(fill=tk.BOTH, padx=5, pady=2)
            self.create_image_list_item(frame, img_file, idx)

    # 图片卡创建
    def create_image_card(self, parent, img_file, index):
        img_path = os.path.join(self.image_dir, img_file)
        photo = self.load_thumbnail(img_path)
        panel = ttk.Label(parent, image=photo, style='Card.TLabel')
        panel.image_ref = photo  # 保持引用
        panel.pack(pady=5)
        name_label = ttk.Label(parent, text=os.path.splitext(img_file)[0], wraplength=150)
        name_label.pack(fill=tk.X, padx=5)
        parent.bind("<Button-1>", lambda e, i=index: self.select_image(i))
        panel.bind("<Button-1>", lambda e, i=index: self.select_image(i))
        name_label.bind("<Button-1>", lambda e, i=index: self.select_image(i))
        panel.bind("<Double-1>", lambda e, path=img_path: self.show_preview(path))

    # 列表项创建
    def create_image_list_item(self, parent, img_file, index):
        img_path = os.path.join(self.image_dir, img_file)
        photo = self.load_thumbnail(img_path, (60, 60))
        img_label = ttk.Label(parent, image=photo)
        img_label.image_ref = photo  # 保持引用
        img_label.pack(side=tk.LEFT, padx=5)
        text_frame = ttk.Frame(parent)
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        text_label = ttk.Label(text_frame, text=os.path.basename(img_file), font=('微软雅黑', 10, 'bold'), width=500)
        text_label.pack(anchor=tk.W)
        for widget in (text_frame, text_label):
            widget.bind("<Button-1>", lambda e, i=index: self.select_image(i))
        parent.bind("<Button-1>", lambda e, i=index: self.select_image(i))

    # 预览方法
    def show_preview(self, path):
        photo = self.load_preview(path)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.preview_canvas.image_ref = photo  # 保持引用

    # 异步化翻译标签
    def translate_tags(self):
        current_image = self.image_files[self.current_image_index]
        original = self.tag_data.get(current_image, "")
        trans_win = self.create_center_window("翻译对照", 600, 450)
        trans_win.resizable(True, True)
        ttk.Label(trans_win, text="原文:", font=('微软雅黑', 10, 'bold')).pack(anchor=tk.W, padx=10, pady=5)
        orig_text = ScrolledText(trans_win, height=5, wrap=tk.WORD)
        orig_text.insert(tk.END, original)
        orig_text.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(trans_win, text="译文:", font=('微软雅黑', 10, 'bold')).pack(anchor=tk.W, padx=10, pady=5)
        trans_text = ScrolledText(trans_win, height=10, wrap=tk.WORD)
        trans_text.pack(fill=tk.X, padx=10, pady=5)
        trans_text.config(state=tk.DISABLED)
        button_frame = ttk.Frame(trans_win)
        button_frame.pack(pady=5)

        # 保存修改按钮
        def save_original_edit():
            new_content = orig_text.get("1.0", tk.END).strip()
            self.tag_data[current_image] = new_content
            self.save_tags()
            self.update_tag_editor()
            messagebox.showinfo("提示", "原文已保存", parent=trans_win)

        save_btn = ttk.Button(button_frame, text="保存修改", command=save_original_edit, style='success.TButton')
        save_btn.pack(side=tk.LEFT, padx=5)

        # 翻译按钮
        def update_translation():
            query = orig_text.get("1.0", tk.END).strip()
            self.translate_api_async(query, self.target_language,
                                     lambda res: self.update_translation_result(trans_text, res))

        translate_btn = ttk.Button(button_frame, text="立即翻译", command=update_translation, style='primary.TButton')
        translate_btn.pack(side=tk.LEFT, padx=5)

    # 异步更新翻译结果
    def update_translation_result(self, text_widget, result):
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, result)
        text_widget.config(state=tk.DISABLED)

    # 批量保存优化
    def save_tags(self):
        current_image = self.image_files[self.current_image_index]
        tag_file = os.path.splitext(current_image)[0] + ".txt"

        def batch_save():
            with open(os.path.join(self.image_dir, tag_file), 'w', encoding='utf-8') as f:
                f.write(self.tag_data[current_image])

        threading.Thread(target=batch_save).start()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="打开目录", command=self.load_directory, accelerator="Ctrl+O")
        self.history_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="最近打开", menu=self.history_menu)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="批量添加", command=self.batch_add_tags, accelerator="Ctrl+B")
        edit_menu.add_command(label="批量替换", command=self.batch_replace_tags)
        edit_menu.add_command(label="批量删除", command=self.batch_delete_tags)
        menubar.add_cascade(label="编辑", menu=edit_menu)
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="切换宫格视图", command=self.toggle_grid_view, accelerator="Ctrl+G")
        view_menu.add_command(label="切换列表视图", command=self.toggle_list_view, accelerator="Ctrl+L")
        menubar.add_cascade(label="视图", menu=view_menu)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="翻译配置", command=self.show_settings)
        settings_menu.add_command(label="宫格设置", command=self.show_grid_settings)
        menubar.add_cascade(label="设置", menu=settings_menu)
        self.root.config(menu=menubar)
        self.root.bind_all("<Control-o>", lambda e: self.load_directory())
        self.root.bind_all("<Control-g>", lambda e: self.toggle_grid_view())
        self.root.bind_all("<Control-l>", lambda e: self.toggle_list_view())
        self.root.bind_all("<Control-b>", lambda e: self.batch_add_tags())

    def update_history_menu(self):
        self.history_menu.delete(0, tk.END)
        for directory in self.history_dirs:
            self.history_menu.add_command(
                label=directory,
                command=lambda d=directory: self.load_directory(directory=d)
            )
        if not self.history_dirs:
            self.history_menu.add_command(
                label="（无记录）",
                state=tk.DISABLED
            )

    def create_main_pane(self):
        self.paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_left_panel(self):
        left_frame = ttk.Frame(self.paned_window, padding=5)
        left_frame.grid_rowconfigure(0, weight=0)
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_rowconfigure(2, weight=0)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_columnconfigure(1, weight=0)
        toolbar = ttk.Frame(left_frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 5))
        self.grid_btn = ttk.Button(toolbar, text="宫格视图", command=self.toggle_grid_view, style='primary.Outline.TButton')
        self.grid_btn.pack(side=tk.LEFT, padx=2)
        self.list_btn = ttk.Button(toolbar, text="列表视图", command=self.toggle_list_view, style='primary.Outline.TButton')
        self.list_btn.pack(side=tk.LEFT, padx=2)
        self.canvas = tk.Canvas(left_frame, bg='white', highlightthickness=1, highlightbackground="#ddd")
        self.v_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.h_scroll = ttk.Scrollbar(left_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.grid(row=1, column=0, sticky='nsew', padx=(0, 5))
        self.v_scroll.grid(row=1, column=1, sticky='ns')
        self.h_scroll.grid(row=2, column=0, columnspan=2, sticky='ew')
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.v_scroll.set, xscrollcommand=self.h_scroll.set)
        self.canvas.bind("<Enter>", lambda _: self.canvas.bind_all("<MouseWheel>", self.on_mousewheel))
        self.canvas.bind("<Leave>", lambda _: self.canvas.unbind_all("<MouseWheel>"))
        self.paned_window.add(left_frame, weight=3)

    def create_right_panel(self):
        right_frame = ttk.Frame(self.paned_window, padding=5)
        self.tab_control = ttk.Notebook(right_frame)
        self.tab_control.pack(fill=tk.BOTH, expand=True, pady=5)
        self.tag_frame = ttk.Frame(self.tab_control)
        preview_frame = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tag_frame, text='标签编辑')
        self.tab_control.add(preview_frame, text='图片预览')
        self.tag_notebook = ttk.Notebook(self.tag_frame)
        self.tag_notebook.pack(fill=tk.BOTH, expand=True)
        self.full_frame = ttk.Frame(self.tag_notebook)
        self.full_text = ScrolledText(self.full_frame, height=10)
        self.full_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        button_frame = ttk.Frame(self.full_frame)
        button_frame.pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="保存修改", command=self.update_full_tags, style='success.TButton').pack(side=tk.LEFT,
                                                                                                           padx=2)
        ttk.Button(button_frame, text="翻译标签", command=self.translate_tags, style='primary.TButton').pack(side=tk.LEFT,
                                                                                                         padx=2)
        self.tag_editor_frame = ttk.Frame(self.tag_notebook)
        self.tag_canvas = tk.Canvas(self.tag_editor_frame, bg='white', highlightthickness=0)
        self.tag_scroll = ttk.Scrollbar(self.tag_editor_frame, orient=tk.VERTICAL, command=self.tag_canvas.yview)
        self.tag_scrollable = ttk.Frame(self.tag_canvas)
        self.tag_scrollable.bind(
            "<Configure>",
            lambda e: self.tag_canvas.configure(scrollregion=self.tag_canvas.bbox("all"))
        )
        self.tag_canvas.create_window((0, 0), window=self.tag_scrollable, anchor="nw")
        self.tag_canvas.configure(yscrollcommand=self.tag_scroll.set)
        self.tag_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tag_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tag_canvas.bind("<Enter>", self.enable_tag_scroll)
        self.tag_canvas.bind("<Leave>", self.disable_tag_scroll)
        self.tag_notebook.add(self.full_frame, text='完整编辑')
        self.tag_notebook.add(self.tag_editor_frame, text='标签管理')
        self.preview_canvas = tk.Canvas(preview_frame, bg='white', highlightthickness=1, highlightbackground="#ddd")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.paned_window.add(right_frame, weight=2)

    def enable_tag_scroll(self, event):
        self.tag_canvas.bind_all("<MouseWheel>", self.on_tag_scroll)

    def disable_tag_scroll(self, event):
        self.tag_canvas.unbind_all("<MouseWheel>")

    def on_tag_scroll(self, event):
        if self.tag_canvas.winfo_exists():
            self.tag_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def set_initial_sash(self):
        if self.paned_window.winfo_exists():
            window_width = self.paned_window.winfo_width()
            if window_width > 0:
                self.paned_window.sashpos(0, int(window_width * 0.6))
            else:
                self.root.after(100, self.set_initial_sash)

    def create_status_bar(self):
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_label = ttk.Label(self.status_bar, text="就绪", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=5, pady=2)
        self.progress = ttk.Progressbar(self.status_bar, mode='indeterminate', length=100)
        self.progress.pack(side=tk.RIGHT, padx=5, pady=2)

    def toggle_grid_view(self):
        self.view_mode = "grid"
        self.show_grid_view()
        self.grid_btn.config(style='primary.TButton')
        self.list_btn.config(style='primary.Outline.TButton')

    def toggle_list_view(self):
        self.view_mode = "list"
        self.show_list_view()
        self.list_btn.config(style='primary.TButton')
        self.grid_btn.config(style='primary.Outline.TButton')

    def clear_view(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

    def select_image(self, index):
        if index >= len(self.image_files):
            return
        if self.current_image_index == index:
            return
        self.clear_selection()
        self.current_image_index = index
        if self.view_mode == "grid":
            row, col = divmod(index, self.grid_cols)  # 使用动态列数
            try:
                current_frame = self.scrollable_frame.grid_slaves(row=row, column=col)[0]
                current_frame.config(style='Selected.TFrame')
            except IndexError:
                print(f"IndexError: Row={row}, Col={col}, Index={index}")
        else:
            children = self.scrollable_frame.pack_slaves()
            if index < len(children):
                current_frame = children[index]
                current_frame.config(style='Selected.TFrame')
        self.show_preview(os.path.join(self.image_dir, self.image_files[index]))
        self.update_tag_editor()

    def clear_selection(self):
        if self.view_mode == "grid":
            for widget in self.scrollable_frame.grid_slaves():
                widget.config(style='TFrame')
        else:
            for widget in self.scrollable_frame.pack_slaves():
                widget.config(style='TFrame')

    def show_preview(self, path):
        photo = self.load_preview(path)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.preview_canvas.image_ref = photo

    def update_tag_editor(self):
        current_image = self.image_files[self.current_image_index]
        tags = self.tag_data.get(current_image, "")
        self.full_text.delete(1.0, tk.END)
        self.full_text.insert(tk.END, tags)
        for widget in self.tag_scrollable.winfo_children():
            widget.destroy()
        self.create_tag_controls()
        for tag in tags.split(','):
            self.create_tag_widget(tag.strip())

    def create_tag_controls(self):
        control_frame = ttk.Frame(self.tag_scrollable)
        control_frame.pack(fill=tk.X, pady=5)
        self.add_position = tk.StringVar(value="back")
        ttk.Radiobutton(control_frame, text="最前面", variable=self.add_position, value="front").pack(side=tk.RIGHT,
                                                                                                   padx=2)
        ttk.Radiobutton(control_frame, text="最后面", variable=self.add_position, value="back").pack(side=tk.RIGHT, padx=2)
        self.tag_entry = ttk.Entry(control_frame, font=('微软雅黑', 10))
        self.tag_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        add_btn = ttk.Button(control_frame, text="+ 添加", command=self.add_tag, style='success.Outline.TButton')
        add_btn.pack(side=tk.RIGHT, padx=5)

    def create_tag_widget(self, tag):
        if not tag:
            return
        tag_frame = ttk.Frame(self.tag_scrollable, style='Card.TFrame', padding=5)
        tag_frame.pack(fill=tk.X, pady=2)
        entry_var = tk.StringVar(value=tag)
        entry = ttk.Entry(tag_frame, textvariable=entry_var, font=('微软雅黑', 10))
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        btn_frame = ttk.Frame(tag_frame)
        btn_frame.pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="×", width=2, style='danger.Outline.TButton',
                   command=lambda: self.remove_tag(tag)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="↑", width=2, style='primary.Outline.TButton',
                   command=lambda: self.move_tag_up(tag)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="↓", width=2, style='primary.Outline.TButton',
                   command=lambda: self.move_tag_down(tag)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="译", width=2, style='info.Outline.TButton',
                   command=lambda: self.translate_single_tag(tag)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="✓", width=2, style='success.Outline.TButton',
                   command=lambda: self.save_tag(tag, entry_var.get())).pack(side=tk.LEFT, padx=2)

    def show_settings(self):
        win = self.create_center_window("百度翻译配置", 400, 250)
        ttk.Label(win, text="APPID:", font=('微软雅黑', 10)).pack(padx=20, pady=5, anchor=tk.W)
        appid_entry = ttk.Entry(win, font=('微软雅黑', 10))
        appid_entry.insert(0, self.baidu_appid)
        appid_entry.pack(padx=20, pady=5, fill=tk.X)
        ttk.Label(win, text="API Token:", font=('微软雅黑', 10)).pack(padx=20, pady=5, anchor=tk.W)
        token_entry = ttk.Entry(win, font=('微软雅黑', 10))
        token_entry.insert(0, self.baidu_token)
        token_entry.pack(padx=20, pady=5, fill=tk.X)
        save_btn = ttk.Button(win, text="保存配置", style='primary.TButton',
                              command=lambda: self.save_config(appid_entry.get(), token_entry.get(), win))
        save_btn.pack(pady=20)

    def show_grid_settings(self):
        win = self.create_center_window("宫格设置", 300, 150)
        ttk.Label(win, text="每行显示图片数:", font=('微软雅黑', 10)).pack(padx=20, pady=5, anchor=tk.W)
        cols_entry = ttk.Entry(win, font=('微软雅黑', 10))
        cols_entry.insert(0, str(self.grid_cols))
        cols_entry.pack(padx=20, pady=5, fill=tk.X)

        def apply_settings():
            try:
                new_cols = int(cols_entry.get())
                if new_cols < 1:
                    raise ValueError("列数必须大于0")
                self.grid_cols = new_cols
                self.save_all_config()  # 保存新配置
                if self.view_mode == "grid":
                    self.show_grid_view()  # 更新宫格视图
                win.destroy()
            except ValueError as e:
                messagebox.showerror("错误", f"无效的列数：{str(e)}", parent=win)

        ttk.Button(win, text="确定", command=apply_settings, style='success.TButton').pack(pady=10)

    def translate_api(self, query, to_lang="zh"):
        appid = self.baidu_appid
        token = self.baidu_token
        if not appid or not token:
            return "请先配置百度翻译参数"
        from_lang = "auto"
        endpoint = "https://fanyi-api.baidu.com"
        path = "/api/trans/vip/translate"
        url = endpoint + path
        salt = random.randint(10000, 99999)
        sign_str = f"{appid}{query}{salt}{token}"
        sign = md5(sign_str.encode()).hexdigest()
        params = {
            "appid": appid,
            "q": query,
            "from": from_lang,
            "to": to_lang,
            "salt": salt,
            "sign": sign
        }
        try:
            response = requests.post(url, data=params, proxies={})
            result = response.json()
            if 'error_code' in result:
                return f"翻译失败：{result['error_msg']}"
            return "\n".join([item['dst'] for item in result['trans_result']])
        except Exception as e:
            return f"请求失败：{str(e)}"
        finally:
            time.sleep(1)

    def batch_add_tags(self):
        def apply():
            new_tag = entry.get().strip()
            position = position_var.get()
            if new_tag:
                for img in self.image_files:
                    current_tags = self.tag_data.get(img, "")
                    if position == "front":
                        self.tag_data[img] = new_tag + (f",{current_tags}" if current_tags else "")
                    else:
                        self.tag_data[img] += ("," if current_tags else "") + new_tag
                    self.save_tags()
                win.destroy()
                self.update_tag_editor()

        win = self.create_center_window("批量添加标签", 300, 170)
        ttk.Label(win, text="添加标签:").pack(padx=10, pady=5)
        entry = ttk.Entry(win, font=('微软雅黑', 10))
        entry.pack(padx=10, pady=5, fill=tk.X)
        position_var = tk.StringVar(value="front")
        ttk.Radiobutton(win, text="最前面", variable=position_var, value="front").pack()
        ttk.Radiobutton(win, text="最后面", variable=position_var, value="back").pack()
        ttk.Button(win, text="确定", command=apply, style='success.TButton').pack(pady=10)

    def batch_replace_tags(self):
        def apply():
            old = old_entry.get().strip()
            new = new_entry.get().strip()
            if old:
                for img in self.image_files:
                    tags = self.tag_data.get(img, "")
                    self.tag_data[img] = tags.replace(old, new)
                    self.save_tags()
                win.destroy()
                self.update_tag_editor()

        win = self.create_center_window("批量替换标签", 300, 200)
        ttk.Label(win, text="替换标签:").pack(padx=10, pady=5)
        old_entry = ttk.Entry(win, font=('微软雅黑', 10))
        old_entry.pack(padx=10, pady=5, fill=tk.X)
        ttk.Label(win, text="替换为:").pack(padx=10, pady=5)
        new_entry = ttk.Entry(win, font=('微软雅黑', 10))
        new_entry.pack(padx=10, pady=5, fill=tk.X)
        ttk.Button(win, text="确定", command=apply, style='success.TButton').pack(pady=10)

    def batch_delete_tags(self):
        def apply():
            target = entry.get().strip()
            if target:
                for img in self.image_files:
                    tags = [t.strip() for t in self.tag_data.get(img, "").split(',') if t.strip() != target]
                    self.tag_data[img] = ",".join(tags)
                    self.save_tags()
                win.destroy()
                self.update_tag_editor()

        win = self.create_center_window("批量删除标签", 300, 120)
        ttk.Label(win, text="删除标签:").pack(padx=10, pady=5)
        entry = ttk.Entry(win, font=('微软雅黑', 10))
        entry.pack(padx=10, pady=5, fill=tk.X)
        ttk.Button(win, text="确定", command=apply, style='danger.TButton').pack(pady=10)

    def save_config(self, appid, token, window):
        self.baidu_appid = appid
        self.baidu_token = token
        self.save_all_config()
        messagebox.showinfo("提示", "配置已保存", parent=window)
        window.destroy()

    def show_progress(self):
        self.progress.start(10)
        self.progress.pack(side=tk.RIGHT, padx=5, pady=2)

    def hide_progress(self):
        self.progress.stop()
        self.progress.pack_forget()

    def update_status(self, message):
        self.status_label.config(text=message)

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def save_tag(self, old_tag, new_tag):
        if old_tag == new_tag.strip():
            return
        current_image = self.image_files[self.current_image_index]
        tags = [t.strip() for t in self.tag_data[current_image].split(',')]
        if old_tag in tags:
            idx = tags.index(old_tag)
            tags[idx] = new_tag.strip()
            self.tag_data[current_image] = ",".join(tags)
            self.save_tags()
            self.update_tag_editor()

    def add_tag(self):
        new_tag = self.tag_entry.get().strip()
        if not new_tag:
            return
        current_image = self.image_files[self.current_image_index]
        current_tags = self.tag_data.get(current_image, "").split(',')
        current_tags = [t.strip() for t in current_tags if t.strip()]
        if self.add_position.get() == "front":
            current_tags.insert(0, new_tag)
        else:
            current_tags.append(new_tag)
        self.tag_data[current_image] = ",".join(current_tags)
        self.save_tags()
        self.update_tag_editor()
        self.tag_entry.delete(0, tk.END)

    def remove_tag(self, old_tag):
        current_image = self.image_files[self.current_image_index]
        tags = [t.strip() for t in self.tag_data[current_image].split(',') if t.strip() != old_tag]
        self.tag_data[current_image] = ",".join(tags)
        self.save_tags()
        self.update_tag_editor()

    def move_tag_up(self, tag):
        current_image = self.image_files[self.current_image_index]
        tags = self.tag_data[current_image].split(',')
        tags = [t.strip() for t in tags]
        if tag in tags:
            idx = tags.index(tag)
            if idx > 0:
                tags[idx], tags[idx - 1] = tags[idx - 1], tags[idx]
                self.tag_data[current_image] = ",".join(tags)
                self.update_tag_editor()
                self.save_tags()

    def move_tag_down(self, tag):
        current_image = self.image_files[self.current_image_index]
        tags = self.tag_data[current_image].split(',')
        tags = [t.strip() for t in tags]
        if tag in tags:
            idx = tags.index(tag)
            if idx < len(tags) - 1:
                tags[idx], tags[idx + 1] = tags[idx + 1], tags[idx]
                self.tag_data[current_image] = ",".join(tags)
                self.update_tag_editor()
                self.save_tags()

    def translate_single_tag(self, tag):
        current_image = self.image_files[self.current_image_index]
        original = tag.strip()  # 当前选中的标签文本

        trans_win = self.create_center_window("翻译对照", 400, 300)
        trans_win.resizable(True, True)

        # 创建原文编辑区
        ttk.Label(trans_win, text="原文:", font=('微软雅黑', 10, 'bold')).pack(anchor=tk.W, padx=10, pady=5)
        orig_text = ScrolledText(trans_win, height=3, wrap=tk.WORD)
        orig_text.insert(tk.END, original)
        orig_text.pack(fill=tk.X, padx=10, pady=5)

        # 创建译文显示区
        ttk.Label(trans_win, text="译文:", font=('微软雅黑', 10, 'bold')).pack(anchor=tk.W, padx=10, pady=5)
        trans_text = ScrolledText(trans_win, height=5, wrap=tk.WORD)
        trans_text.pack(fill=tk.X, padx=10, pady=5)
        trans_text.config(state=tk.DISABLED)

        # 创建按钮区域
        button_frame = ttk.Frame(trans_win)
        button_frame.pack(pady=10)

        # 定义翻译更新函数
        def update_translation():
            query = orig_text.get("1.0", tk.END).strip()
            translated = self.translate_api(query, self.target_language)
            trans_text.config(state=tk.NORMAL)
            trans_text.delete(1.0, tk.END)
            trans_text.insert(tk.END, translated)
            trans_text.config(state=tk.DISABLED)

        # 定义保存修改函数
        def save_modified():
            new_content = orig_text.get("1.0", tk.END).strip()
            current_tags = self.tag_data[current_image].split(',')
            current_tags = [t.strip() for t in current_tags]
            if original in current_tags:
                idx = current_tags.index(original)
                current_tags[idx] = new_content
                self.tag_data[current_image] = ",".join(current_tags)
                self.save_tags()
                self.update_tag_editor()
                messagebox.showinfo("提示", "标签已更新", parent=trans_win)
            trans_win.destroy()

        # 添加按钮
        ttk.Button(button_frame, text="翻译", command=update_translation, style='primary.TButton').pack(side=tk.LEFT,
                                                                                                      padx=5)
        ttk.Button(button_frame, text="保存", command=save_modified, style='success.TButton').pack(side=tk.LEFT, padx=5)

        # 窗口打开时自动翻译
        update_translation()

    def save_tags(self):
        current_image = self.image_files[self.current_image_index]
        tag_file = os.path.splitext(current_image)[0] + ".txt"

        def batch_save():
            with open(os.path.join(self.image_dir, tag_file), 'w', encoding='utf-8') as f:
                f.write(self.tag_data[current_image])

        threading.Thread(target=batch_save).start()

    def update_full_tags(self):
        current_image = self.image_files[self.current_image_index]
        new_tags = self.full_text.get("1.0", tk.END).strip()
        self.tag_data[current_image] = new_tags
        self.save_tags()
        self.update_tag_editor()

    def create_center_window(self, title, width, height):
        win = tk.Toplevel(self.root)
        win.title(title)
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        win.geometry(f"{width}x{height}+{x}+{y}")
        return win

    def load_config(self):
        config = configparser.ConfigParser()
        self.baidu_appid = ""
        self.baidu_token = ""
        try:
            if self.config_path.exists():
                config.read(self.config_path, encoding='utf-8')
                if 'GRID' in config:
                    self.grid_cols = int(config['GRID'].get('cols', '4'))  # 默认值为4
                if 'BAIDU' in config:
                    self.baidu_appid = config['BAIDU'].get('appid', '')
                    self.baidu_token = config['BAIDU'].get('token', '')
                if 'HISTORY' in config:
                    dirs_str = config['HISTORY'].get('directories', '')
                    self.history_dirs = [d.strip() for d in dirs_str.split(',') if d.strip()]
        except Exception as e:
            print(f"配置加载失败：{str(e)}")

    def save_all_config(self):
        config = configparser.ConfigParser()
        config['BAIDU'] = {
            'appid': self.baidu_appid,
            'token': self.baidu_token
        }
        config['HISTORY'] = {
            'directories': ','.join(self.history_dirs)
        }
        config['GRID'] = {
            'cols': str(self.grid_cols)  # 保存宫格列数
        }
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                config.write(f)
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败：{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageTagManager(root)
    root.mainloop()