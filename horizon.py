import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess
import shutil
import json
import threading
import webbrowser
import requests
import sys

class AnnouncementWindow(tk.Toplevel):
    """公告窗口"""
    def __init__(self, master=None):
        super().__init__(master)
        self.title("公告")
        self.geometry("400x300")  # 设置窗口大小
        self.resizable(False, False)

        # 创建 Text 控件，并设置字体
        self.text_area = tk.Text(self, wrap=tk.WORD, state=tk.DISABLED, font=("Arial", 14))  # 设置字体和大小
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        close_button = ttk.Button(self, text="关闭", command=self.destroy)
        close_button.pack(pady=5)

        self.load_announcement()

    def load_announcement(self):
        """从 GitHub Gist 加载公告内容"""
        gist_id = "123"  # 替换为您的 Gist ID
        github_token = "123"  # 替换为您的 GitHub Token

        headers = {
            "Authorization": f"token {github_token}"
        }
        try:
            response = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
            response.raise_for_status()  # 检查请求是否成功
            gist_data = response.json()
            # print(gist_data)  # 调试用,需要可以取消注释
            raw_url = gist_data['files']["Horizon_info.txt"]['raw_url'] #获取第一个文件的 URL


            # 获取公告文本内容
            response_text = requests.get(raw_url)
            response_text.raise_for_status()
            announcement_text = response_text.text

            # 更新 Text 控件的内容
            self.text_area.config(state=tk.NORMAL)  # 先设置为可编辑状态
            self.text_area.delete("1.0", tk.END)  # 清空原有内容
            self.text_area.insert(tk.END, announcement_text)  # 插入新内容
            self.text_area.config(state=tk.DISABLED)  # 设置为只读

        except requests.exceptions.RequestException as e:
            messagebox.showerror("错误", f"无法获取公告内容:\n{e}")
        except (KeyError, IndexError) as e:
            messagebox.showerror("错误", f"解析公告数据时出错:\n{e}")
        except Exception as e:
            messagebox.showerror("错误",f"加载公告失败:\n{e}")

class CS2Configurator:
    announcement_shown = False

    def __init__(self, master):
        self.master = master
        master.title("Horizon")
        master.resizable(True, True)

        # --- UI Elements ---
        self.main_frame = ttk.Frame(master, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)

        # 标签页
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # 状态栏
        self.status_label = ttk.Label(self.main_frame, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # 初始化配置和路径变量 *先于* create_settings_tab
        self.csgo_root_path = tk.StringVar()
        self.config = {}
        self.config_loaded = False

        # 设置配置文件路径 (AppData)
        self.config_dir = os.path.join(os.getenv('APPDATA'), 'Horizon')
        self.config_file_path = os.path.join(self.config_dir, 'Horizon_config.json')

        # 确保配置文件夹存在
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建配置文件夹: {e}")
                # 可以考虑退出程序，因为无法创建配置文件夹
                sys.exit(1)

        # 加载配置
        self.load_config_from_appdata()
        
        # 设置标签页 *后于* 变量初始化
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="设置")
        self.create_settings_tab()

        # 新增：关于标签页
        self.about_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.about_tab, text="关于")
        self.create_about_tab()


        # 首次启动或路径为空时，弹出文件夹选择
        if not self.csgo_root_path.get():
            self.browse_for_csgo_root(initial_browse=True)
        else:
            # 如果启动时有路径，尝试安装
            if self.is_valid_csgo_root(self.csgo_root_path.get()):
                self.auto_install()


    def create_settings_tab(self):
        # CS:GO 根目录选择
        ttk.Label(self.settings_tab, text="CS2 根目录:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.path_entry = ttk.Entry(self.settings_tab, textvariable=self.csgo_root_path, width=40, state="readonly")
        self.path_entry.grid(row=1, column=0, padx=(0, 5), sticky=(tk.W, tk.E))
        browse_button = ttk.Button(self.settings_tab, text="浏览", command=self.browse_for_csgo_root)
        browse_button.grid(row=1, column=1, sticky=tk.W)

        # 使用 Frame 来包含按钮，以便更好地控制布局
        button_frame = ttk.Frame(self.settings_tab)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        # 保存路径按钮
        self.save_button = ttk.Button(button_frame, text="保存路径", command=self.save_config)
        self.save_button.grid(row=0, column=0, padx=5)

        # 新增按钮: 功能设置
        opt_config_button = ttk.Button(button_frame, text="功能设置", command=self.open_opt_config)
        opt_config_button.grid(row=0, column=1, padx=5)

        # 新增按钮: 按键设置
        key_config_button = ttk.Button(button_frame, text="按键设置", command=self.open_key_config)
        key_config_button.grid(row=0, column=2, padx=5)

        #新增按钮：一键清除cfg
        clear_cfg_button = ttk.Button(button_frame, text="一键清除CFG", command=self.clear_cfg)
        clear_cfg_button.grid(row=0, column=3, padx=5)

        # 新增：清除缓存按钮
        clear_cache_button = ttk.Button(button_frame, text="清除缓存", command=self.clear_cache)
        clear_cache_button.grid(row=0, column=4, padx=5)

        self.settings_tab.columnconfigure(0, weight=1)

    def create_about_tab(self):
        """创建“关于”标签页的内容"""
        ttk.Label(self.about_tab, text="版本号：Horizon 5.0", font=("Arial", 12)).pack(pady=10)
        ttk.Label(self.about_tab, text="作者：-Cap1taL-", font=("Arial", 12)).pack(pady=5)

        # 软件官网链接（可点击）
        website_label = ttk.Label(self.about_tab, text="软件官网：https://horizoncfg.top", foreground="blue", cursor="hand2")
        website_label.pack(pady=5)
        website_label.bind("<Button-1>", lambda e: webbrowser.open("https://horizoncfg.top"))

    def browse_for_csgo_root(self, initial_browse=False):
        """打开文件夹选择对话框，让用户选择 CS2 根目录。"""
        initial_dir = self.csgo_root_path.get() if self.csgo_root_path.get() else os.path.expanduser("~")
        directory = filedialog.askdirectory(initialdir=initial_dir, title="选择 CS2 根目录")

        if directory:
            self.csgo_root_path.set(directory)
            if self.is_valid_csgo_root(directory):
                # 路径有效后，加载或创建配置
                if not self.config_loaded:
                    self.load_config_from_appdata()

                # 检查 Horizon 文件夹是否存在，如果不存在则自动安装
                cfg_path = os.path.join(directory, "game", "csgo", "cfg")
                horizon_path = os.path.join(cfg_path, "Horizon")
                if not os.path.exists(horizon_path):
                    self.auto_install()  # 自动安装
                else:
                    self.check_install_status() #更新状态


    def load_config_from_appdata(self):
        """从 AppData 目录下的 Horizon_config.json 文件加载配置"""
        try:
            with open(self.config_file_path, "r") as f:
                self.config = json.load(f)
                self.csgo_root_path.set(self.config.get("csgo_root_path", ""))
            self.config_loaded = True  # 标记配置已加载
        except (FileNotFoundError, json.JSONDecodeError):
            # 文件不存在或 JSON 格式错误
            self.create_and_save_config()  # 创建

    def create_and_save_config(self):
        """创建并保存 Horizon_config.json 文件"""
        self.config = {"csgo_root_path": self.csgo_root_path.get()}
        try:
            with open(self.config_file_path, "w") as f:
                json.dump(self.config, f, indent=4)
            self.config_loaded = True
        except Exception as e:
            messagebox.showerror("错误", f"创建配置文件失败: {e}")


    def save_config(self):
        """保存配置到 AppData 目录下的 Horizon_config.json 文件"""
        path = self.csgo_root_path.get()
        if not path or not self.is_valid_csgo_root(path):
            messagebox.showerror("错误", "请先选择有效的 CS2 根目录。")
            return

        self.config["csgo_root_path"] = path
        try:
            with open(self.config_file_path, "w") as f:
                json.dump(self.config, f, indent=4)
            messagebox.showinfo("已保存", "CS2 根目录路径已保存。")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")

    def is_valid_csgo_root(self, path):
        """检查给定的路径是否是有效的 CS2 根目录。"""
        expected_path = os.path.join(path, "game", "csgo", "cfg")
        if not os.path.isdir(expected_path):
            messagebox.showerror("错误", "无效的 CS2 根目录。未找到 'game\\csgo\\cfg' 文件夹。")
            return False
        return True

    def check_install_status(self):
        """检查安装状态,并更新状态"""
        csgo_root = self.csgo_root_path.get()
        if not csgo_root or not self.is_valid_csgo_root(csgo_root):
            return
        cfg_path = os.path.join(csgo_root, "game", "csgo", "cfg")
        horizon_path = os.path.join(cfg_path, "Horizon")
        if os.path.exists(horizon_path):
            self.status_label.config(text="Horizon 已安装")
        else:
            self.status_label.config(text="就绪")

    def auto_install(self):
        """自动检查并安装 Horizon CFG"""
        csgo_root = self.csgo_root_path.get()
        if not csgo_root or not self.is_valid_csgo_root(csgo_root):
            return

        install_thread = threading.Thread(target=self.install_in_thread, args=(csgo_root,))
        install_thread.start()

    def install_in_thread(self, csgo_root):
        """在单独的线程中执行安装操作"""
        cfg_path = os.path.join(csgo_root, "game", "csgo", "cfg")
        horizon_path = os.path.join(cfg_path, "Horizon")
        if os.path.exists(horizon_path):
            self.master.after(0, self.update_status_label, "Horizon 已安装")
            return

        script_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        local_horizon_path = os.path.join(script_dir, "Horizon")

        if not os.path.exists(local_horizon_path):
            self.master.after(0, messagebox.showerror, "错误", "未找到 Horizon 文件夹。请确保 'Horizon' 文件夹与此程序在同一目录下。")
            return

        try:
             # 复制文件夹
            print(f"尝试复制文件夹：从 {local_horizon_path} 到 {horizon_path}")
            shutil.copytree(local_horizon_path, horizon_path)
            print("文件夹复制成功")

            install_bat_path = os.path.join(horizon_path, "install.bat")
            print(f"尝试运行批处理文件：{install_bat_path}")
            if not os.path.exists(install_bat_path):
                self.master.after(0, messagebox.showerror, "错误", "未找到 install.bat 文件")
                return

            # 使用 subprocess.run，并完全隐藏控制台窗口
            subprocess.run(
                [install_bat_path],
                cwd=horizon_path,
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=True,
                capture_output=True,
                text=True,
            )

            print("批处理文件运行完成")
            self.master.after(0, self.update_status_label, "Horizon 已安装")  # 更新状态栏
            self.master.after(0, messagebox.showinfo, "成功", "安装完成")

        except subprocess.CalledProcessError as e:
            self.master.after(0, messagebox.showerror, "错误", f"install.bat 执行失败:\n{e.stderr}")
            print(f"捕获到异常: {e}")
        except Exception as e:
            self.master.after(0, messagebox.showerror, "错误", f"自动安装失败: {e}")
            print(f"捕获到异常: {e}")

    def update_status_label(self, text):
        self.status_label.config(text=text)

    def open_opt_config(self):
        """打开 optPreference.cfg 文件"""
        csgo_root = self.csgo_root_path.get()
        if csgo_root and self.is_valid_csgo_root(csgo_root):
            file_path = os.path.join(csgo_root, "game", "csgo", "cfg", "Horizon", "optPreference.cfg")
            try:
                os.startfile(file_path)
            except FileNotFoundError:
                messagebox.showerror("错误", "未找到 optPreference.cfg 文件。")
            except Exception as e:
                messagebox.showerror("错误", f"打开文件时出错: {e}")
        else:
            messagebox.showerror("错误", "请先选择有效的 CS2 根目录。")

    def open_key_config(self):
        """打开 keyPreference.cfg 文件"""
        csgo_root = self.csgo_root_path.get()
        if csgo_root and self.is_valid_csgo_root(csgo_root):
            file_path = os.path.join(csgo_root, "game", "csgo", "cfg", "Horizon", "keyPreference.cfg")
            try:
                os.startfile(file_path)
            except FileNotFoundError:
                messagebox.showerror("错误", "未找到 keyPreference.cfg 文件。")
            except Exception as e:
                messagebox.showerror("错误", f"打开文件时出错: {e}")
        else:
            messagebox.showerror("错误", "请先选择有效的 CS2 根目录。")

    def clear_cfg(self):
        # 获取路径
        csgo_root = self.csgo_root_path.get()
        if not csgo_root or not self.is_valid_csgo_root(csgo_root):
            return
        cfg_path = os.path.join(csgo_root, "game", "csgo", "cfg")
        horizon_path = os.path.join(cfg_path, "Horizon")
        remove_file_path = os.path.join(cfg_path, "Cap1taLB站独家免费.cfg")
        # 弹出确认提示框
        if messagebox.askyesno("确认", "确定要删除 Horizon 文件夹吗？"):
            try:
                if os.path.exists(horizon_path):
                    shutil.rmtree(horizon_path)
                if os.path.exists(remove_file_path):
                    os.remove(remove_file_path)
                self.master.after(0, self.update_status_label, "Horizon 已清除")
                messagebox.showinfo("成功", "Horizon CFG 已成功清除！")
            except Exception as e:
                messagebox.showerror("错误", f"删除文件夹时出错: {e}")
                self.status_label.config(text="清除失败")


    def clear_cache(self):
        """清除 Horizon_config.json 文件中的 CS2 路径数据"""
        if messagebox.askyesno("确认", "确定要清除缓存的 CS2 路径吗？"):
            try:
                with open(self.config_file_path, "w") as f:
                    json.dump({"csgo_root_path": ""}, f, indent=4)  # 写入空路径
                self.csgo_root_path.set("")  # 清空当前显示的路径
                messagebox.showinfo("成功", "CS2 路径缓存已清除。")
                self.status_label.config(text="就绪")  # 重置状态栏
            except Exception as e:
                messagebox.showerror("错误", f"清除缓存失败: {e}")

# --- Main Application ---
if __name__ == "__main__":
    root = tk.Tk()
    # 在创建主窗口后立即显示公告窗口（仅显示一次）
    if not CS2Configurator.announcement_shown:
        announcement_window = AnnouncementWindow(root)
        CS2Configurator.announcement_shown = True

    app = CS2Configurator(root)
    root.mainloop()