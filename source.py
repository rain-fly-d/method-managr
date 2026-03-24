import os
import sys
import json
import glob
import time
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

# ---------- 配置管理 ----------
CONFIG_FILE = "config.json"

class ConfigManager:
    """读写 JSON 配置，存储文件名→路径映射"""
    def __init__(self):
        self.config = {}
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def save(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def add(self, name, path):
        self.config[name] = path
        self.save()

    def remove(self, name):
        if name in self.config:
            del self.config[name]
            self.save()

    def get(self, name):
        return self.config.get(name)

    def items(self):
        return self.config.items()


# ---------- 文件扫描相关 ----------
def get_latest_exe(directory):
    """
    扫描指定目录下所有 .exe 文件，返回最新修改的那个文件的完整路径。
    返回 None 如果没有 .exe 文件。
    """
    pattern = os.path.join(directory, "*.exe")
    files = glob.glob(pattern)
    if not files:
        return None
    # 按修改时间排序，取最新
    latest = max(files, key=os.path.getmtime)
    return latest

def get_filename_from_path(path):
    return os.path.basename(path)


# ---------- 打开文件/文件夹 ----------
def open_target(path):
    """用系统默认方式打开路径（文件夹或文件）"""
    if not os.path.exists(path):
        messagebox.showerror("错误", f"路径不存在: {path}")
        return False
    try:
        os.startfile(path)
        return True
    except Exception as e:
        messagebox.showerror("错误", f"无法打开: {e}")
        return False


# ---------- 配置模式窗口 ----------
class ConfigApp:
    def __init__(self, root):
        self.root = root
        self.root.title("方法管理---作者个人网站rain-fly.top")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f0f0")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.config_mgr = ConfigManager()
        self.work_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.last_triggered_file = None
        self.check_interval = 1000

        # 输入变量
        self.filename_var = tk.StringVar()
        self.path_var = tk.StringVar()

        # 创建主布局
        self.create_widgets()
        self.refresh_list()
        self.start_monitoring()

    def create_widgets(self):
        # 状态栏（顶部）
        self.status_label = tk.Label(
            self.root, text="监控中...", font=("微软雅黑", 10),
            bg="#f0f0f0", fg="#333", anchor="w"
        )
        self.status_label.pack(fill=tk.X, padx=10, pady=(5,0))

        # 中间列表区域
        list_frame = tk.Frame(self.root, bg="#f0f0f0")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 滚动条和树形表格
        self.tree = ttk.Treeview(list_frame, columns=("filename", "path"), show="headings", height=15)
        self.tree.heading("filename", text="文件名")
        self.tree.heading("path", text="目标路径")
        self.tree.column("filename", width=200)
        self.tree.column("path", width=450)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 绑定选中事件：点击列表自动填充到输入框
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)

        # 底部输入区域（两行）
        bottom_frame = tk.Frame(self.root, bg="#f0f0f0")
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)

        # 第一行：输入框
        input_frame = tk.Frame(bottom_frame, bg="#f0f0f0")
        input_frame.pack(fill=tk.X, pady=(0,10))

        # 文件名输入
        tk.Label(input_frame, text="文件名:", width=8, anchor="e", bg="#f0f0f0").pack(side=tk.LEFT, padx=(0,5))
        filename_entry = tk.Entry(input_frame, textvariable=self.filename_var, width=30, font=("Consolas", 10))
        filename_entry.pack(side=tk.LEFT, padx=(0,20))

        # 路径输入
        tk.Label(input_frame, text="目标路径:", width=8, anchor="e", bg="#f0f0f0").pack(side=tk.LEFT, padx=(0,5))
        path_entry = tk.Entry(input_frame, textvariable=self.path_var, width=50, font=("Consolas", 10))
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 第二行：按钮（等间距，带颜色）
        btn_frame = tk.Frame(bottom_frame, bg="#f0f0f0")
        btn_frame.pack(fill=tk.X)

        # 让按钮等间距：使用 grid 布局，设置列权重相等
        for i in range(4):
            btn_frame.columnconfigure(i, weight=1)

        # 添加按钮（绿色）
        self.btn_add = tk.Button(
            btn_frame, text="添加", command=self.add_mapping,
            bg="#4CAF50", fg="white", font=("微软雅黑", 10),
            relief=tk.RAISED, padx=5, pady=3
        )
        self.btn_add.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # 更新按钮（蓝色）
        self.btn_update = tk.Button(
            btn_frame, text="更新", command=self.update_mapping,
            bg="#2196F3", fg="white", font=("微软雅黑", 10),
            relief=tk.RAISED, padx=5, pady=3
        )
        self.btn_update.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # 删除按钮（红色）
        self.btn_delete = tk.Button(
            btn_frame, text="删除", command=self.delete_mapping,
            bg="#f44336", fg="white", font=("微软雅黑", 10),
            relief=tk.RAISED, padx=5, pady=3
        )
        self.btn_delete.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # 刷新按钮（灰色）
        self.btn_refresh = tk.Button(
            btn_frame, text="刷新", command=self.refresh_list,
            bg="#9E9E9E", fg="white", font=("微软雅黑", 10),
            relief=tk.RAISED, padx=5, pady=3
        )
        self.btn_refresh.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

    def on_item_select(self, event):
        """选中列表项时，自动填充输入框"""
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        filename = item['values'][0]
        path = item['values'][1]
        self.filename_var.set(filename)
        self.path_var.set(path)

    def add_mapping(self):
        """添加新映射（若文件名已存在则询问覆盖）"""
        filename = self.filename_var.get().strip()
        path = self.path_var.get().strip()
        if not filename:
            messagebox.showwarning("警告", "文件名不能为空")
            return
        if not path:
            messagebox.showwarning("警告", "目标路径不能为空")
            return
        if not filename.lower().endswith(".exe"):
            filename += ".exe"
            self.filename_var.set(filename)  # 自动补全

        if filename in self.config_mgr.config:
            # 已存在，询问是否覆盖
            if messagebox.askyesno("确认", f"映射 '{filename}' 已存在，是否覆盖其路径？"):
                self.config_mgr.add(filename, path)
                self.refresh_list()
                messagebox.showinfo("成功", f"已更新映射 '{filename}'")
            # 否则不做任何事
        else:
            self.config_mgr.add(filename, path)
            self.refresh_list()
            messagebox.showinfo("成功", f"已添加映射 '{filename}'")

    def update_mapping(self):
        """更新当前选中的映射"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先点击列表选中要更新的条目")
            return
        item = self.tree.item(selected[0])
        old_filename = item['values'][0]
        new_filename = self.filename_var.get().strip()
        new_path = self.path_var.get().strip()

        if not new_filename:
            messagebox.showwarning("警告", "文件名不能为空")
            return
        if not new_path:
            messagebox.showwarning("警告", "目标路径不能为空")
            return
        if not new_filename.lower().endswith(".exe"):
            new_filename += ".exe"
            self.filename_var.set(new_filename)

        # 如果没有任何变化，直接返回
        if old_filename == new_filename and self.config_mgr.get(old_filename) == new_path:
            return

        # 如果新文件名已存在且不是当前条目，询问是否覆盖
        if new_filename != old_filename and new_filename in self.config_mgr.config:
            if not messagebox.askyesno("冲突", f"文件名 '{new_filename}' 已存在，是否覆盖该条目？"):
                return
            # 覆盖：先删除旧条目（如果不同）再添加新条目
            self.config_mgr.remove(old_filename)
            self.config_mgr.add(new_filename, new_path)
        else:
            # 直接更新：删除旧条目，添加新条目
            self.config_mgr.remove(old_filename)
            self.config_mgr.add(new_filename, new_path)

        self.refresh_list()
        # 清空输入框
        self.filename_var.set("")
        self.path_var.set("")
        messagebox.showinfo("成功", f"已更新映射 '{new_filename}'")

    def delete_mapping(self):
        """删除选中的映射"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "请先点击列表选中要删除的条目")
            return
        item = self.tree.item(selected[0])
        filename = item['values'][0]
        if messagebox.askyesno("确认", f"确定要删除映射 '{filename}' 吗？"):
            self.config_mgr.remove(filename)
            self.refresh_list()
            # 如果删除的条目正在输入框中，则清空
            if self.filename_var.get() == filename:
                self.filename_var.set("")
                self.path_var.set("")

    def refresh_list(self):
        """刷新列表显示"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for name, path in self.config_mgr.items():
            self.tree.insert("", tk.END, values=(name, path))

    def start_monitoring(self):
        """启动定时器，监控当前目录下最新 .exe 文件的变化"""
        self.check_latest_exe()

    def check_latest_exe(self):
        """每隔一段时间扫描目录，若最新 .exe 文件名在配置中则打开目标"""
        latest_path = get_latest_exe(self.work_dir)
        if latest_path:
            latest_name = get_filename_from_path(latest_path)
            # 如果最新文件名在配置中，并且不是刚刚触发过的（避免重复）
            target = self.config_mgr.get(latest_name)
            if target and latest_name != self.last_triggered_file:
                # 更新状态栏
                self.status_label.config(text=f"检测到: {latest_name} → 打开 {target}")
                # 打开目标
                open_target(target)
                self.last_triggered_file = latest_name
                # 下一次如果还是同一个文件就不触发了
            else:
                self.status_label.config(text=f"当前最新: {latest_name} (未配置或无变化)")
        else:
            self.status_label.config(text="当前目录无 .exe 文件")
        self.root.after(self.check_interval, self.check_latest_exe)

    def on_close(self):
        self.root.destroy()


# ---------- 执行模式 ----------
def run_execution_mode(exe_name):
    """执行模式：根据当前文件名查找映射，打开目标后退出"""
    cfg = ConfigManager()
    target = cfg.get(exe_name)
    if target:
        open_target(target)
    sys.exit(0)


# ---------- 入口 ----------
def main():
    # 获取启动时的文件名（含 .exe）
    start_name = os.path.basename(sys.argv[0])

    # 如果启动文件名是“方法管理.exe”，进入配置模式
    if start_name.lower() == "方法管理.exe":
        root = tk.Tk()
        app = ConfigApp(root)
        root.mainloop()
    else:
        # 否则进入执行模式
        run_execution_mode(start_name)


if __name__ == "__main__":
    main()