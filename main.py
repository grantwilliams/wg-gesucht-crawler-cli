import os
import sys
import json
import threading
import queue
import multiprocessing
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from idlelib.tooltip import ToolTip
from PIL import Image, ImageTk
import psutil
import wg_gesucht
import create_results_folders


class MainWindow(ttk.Frame):

    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)

        self.parent = parent
        self.pack(fill=tk.BOTH, expand=True)

        self.folder_queue = queue.Queue()

        self.pointer = "pointinghand" if sys.platform == 'darwin' else "hand2"
        choose_info_btn_font = "-size 16" if sys.platform == 'linux' else "-size 18"
        field_width = 35 if sys.platform == "win32" else 30
        home_path = 'HOMEPATH' if sys.platform == 'win32' else 'HOME'
        self.dirname = os.path.join(os.environ[home_path], 'Documents', 'WG Finder')
        self.wg_ad_links = os.path.join(self.dirname, "WG Ad Links")
        self.offline_ad_links = os.path.join(self.dirname, "Offline Ad Links")
        if not os.path.exists(self.wg_ad_links) or not os.path.exists(self.offline_ad_links):
            folder_thread = threading.Thread(target=create_results_folders.create_folders,
                                             args=[self.folder_queue, self.dirname])
            folder_thread.daemon = True
            folder_thread.start()

        choose_info = ttk.Style()
        choose_info.configure("Choose.TButton", font=choose_info_btn_font, padding=(10, 30, 10, 30))
        self.warning_lbl_style = ttk.Style()
        self.warning_lbl_style.configure('Warning.TLabel', foreground="red")
        self.large_warning_lbl_style = ttk.Style()
        self.large_warning_lbl_style.configure('LargeWarning.TLabel', foreground="red")

        self.window_width = 1

        # create GUI title widgets
        self.title_frame = ttk.Frame(self)
        self.title_frame.columnconfigure(0, weight=1)
        self.title_frame.grid(row=0, column=0, padx=20, pady=(10, 20), sticky=tk.W+tk.E)
        self.title_img = Image.open('.images/title.gif' if sys.platform == 'darwin' else '.images/title.png')
        self.title_photo = ImageTk.PhotoImage(self.title_img)
        self.title = ttk.Label(self.title_frame, image=self.title_photo)
        self.title.grid(row=0, column=0)

        #  create Choose Info widgets
        self.choose_info_btn_frame = ttk.Frame(self)
        self.saved_info_btn = ttk.Button(self.choose_info_btn_frame, style="Choose.TButton", cursor=self.pointer,
                                         text="Use saved login details",
                                         command=lambda: self.check_credentials("choose info"))
        self.saved_info_btn_tooltip = ToolTip(self.saved_info_btn, "Log into WG-Gesucht.de with the email and \n"
                                                                   "password you have saved previously and start \n"
                                                                   "searching for new apartments")
        self.update_info_btn = ttk.Button(self.choose_info_btn_frame, style="Choose.TButton", cursor=self.pointer,
                                          text="Update login details",
                                          command=lambda: self.save_login_details("choose info"))
        self.update_info_btn_tooltip = ToolTip(self.update_info_btn, "Update your WG-Gesucht.de password if you have \n"
                                                                     "changed it since running the program last")
        warning_text = "***You seem to have moved or deleted your login info file, if you have moved it, please " \
                       "move it back to the '.data_files' folder, or if you have accidentally deleted it, please " \
                       "email 'wg.finder.de@gmail.com.***"
        self.choose_info_warning_var = tk.StringVar()
        self.choose_info_warning_lbl = ttk.Label(self.choose_info_btn_frame, style="Warning.TLabel",
                                                 textvariable=self.choose_info_warning_var)
        self.no_login_warning = ttk.Label(self.choose_info_btn_frame, text=warning_text, style='LargeWarning.TLabel')

        if not os.path.exists(".data_files"):
            os.makedirs(".data_files")
        self.login_info_file = '.data_files/.login_info.json'
        self.login_info = dict()
        if os.path.isfile(self.login_info_file):
            with open(self.login_info_file) as file:
                self.login_info = json.load(file)
        else:
            with open('.data_files/.login_info.json', 'w', encoding='utf-8') as save:
                json.dump(self.login_info, indent=4, sort_keys=True, fp=save)

        self.check_credentials_queue = queue.Queue()
        self.log_output_queue = multiprocessing.Queue()
        self.main_process = multiprocessing.Process(target=wg_gesucht.start_searching,
                                                    args=[self.login_info, self.log_output_queue, self.wg_ad_links,
                                                          self.offline_ad_links])

        #  create login form widgets
        bullet = "\u2022"
        self.form_frame = ttk.Frame(self)
        self.form_frame.columnconfigure(1, weight=1)
        self.email_lbl = ttk.Label(self.form_frame, text="Email: ")
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(self.form_frame, textvariable=self.email_var, width=field_width)
        self.email_var.set(self.login_info.get("email", ""))
        self.password_lbl = ttk.Label(self.form_frame, text="Password: ")
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(self.form_frame, show=bullet, textvariable=self.password_var, width=field_width)
        self.password_entry.bind("<Return>", lambda event: self.check_credentials('save details'))
        self.phone_number_lbl = ttk.Label(self.form_frame, text="Phone Number: ")
        self.phone_number_var = tk.StringVar()
        self.phone_number_entry = ttk.Entry(self.form_frame, textvariable=self.phone_number_var, width=field_width)
        self.phone_number_entry.bind("<Return>", lambda event: self.check_credentials('save details'))
        self.form_warning_var = tk.StringVar()
        self.form_warning_lbl = ttk.Label(self.form_frame, style='Warning.TLabel', textvariable=self.form_warning_var)
        self.save_button = ttk.Button(self.form_frame, text="Save and Start", cursor=self.pointer,
                                      command=lambda: self.check_credentials('save details'))
        self.form_back_btn = ttk.Button(self.form_frame, text="Back", cursor=self.pointer,
                                        command=lambda: self.choose_info("save details"))

        #  create log window widgets
        self.stop_restart_frame = ttk.Frame(self)
        self.log_stop_button = ttk.Button(self.stop_restart_frame, text="Stop", cursor=self.pointer, command=self.stop)
        self.log_back_button = ttk.Button(self.stop_restart_frame, text="Back", cursor=self.pointer,
                                          command=lambda: self.choose_info("log window"))
        self.log_restart_button = ttk.Button(self.stop_restart_frame, text="Restart", cursor=self.pointer,
                                             command=lambda: self.log_window("restart"))
        self.log_frame = ttk.Frame(self)
        self.log_text = scrolledtext.ScrolledText(self.log_frame, borderwidth=1, relief='sunken', state=tk.DISABLED)

        if self.login_info.get("email", "") == "" or self.login_info.get("password", "") == "":
            self.save_login_details("init")
        else:
            self.choose_info("init")

    def choose_info(self, origin):
        if origin == "log window":
            self.stop_restart_frame.grid_forget()
            self.log_frame.grid_forget()
        if origin == "save details":
            self.form_frame.grid_forget()

        self.choose_info_btn_frame.grid(row=1, column=0, padx=20, sticky=tk.W+tk.E)
        self.saved_info_btn.grid(row=0, column=0, padx=10)
        self.saved_info_btn.configure(state=tk.ACTIVE)
        self.update_info_btn.grid(row=0, column=1, padx=10)
        self.update_info_btn.configure(state=tk.ACTIVE)
        self.choose_info_warning_lbl.grid(row=1, column=0, pady=(10, 20), sticky=tk.W)
        self.choose_info_warning_var.set('')
        self.update_idletasks()

        if origin == "no login file":
            self.update_idletasks()
            self.no_login_warning.configure(wraplength=self.winfo_width() - 20)
            self.no_login_warning.grid(row=2, column=0, columnspan=2)
            self.saved_info_btn.configure(state=tk.DISABLED)
            self.update_info_btn.configure(state=tk.DISABLED)

        self.parent.after(100, self.process_folder_queue())

    def save_login_details(self, origin):
        if origin == "choose info":
            self.choose_info_btn_frame.grid_forget()

        self.form_frame.grid(row=1, column=0, padx=20, sticky=tk.W+tk.E)
        self.email_lbl.grid(row=0, column=0, sticky=tk.E, pady=2)
        self.email_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W+tk.E, pady=2)
        self.email_entry.focus()
        self.password_lbl.grid(row=1, column=0, sticky=tk.E, pady=2)
        self.password_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W+tk.E, pady=2)
        self.password_entry.delete(0, tk.END)
        self.phone_number_lbl.grid(row=3, column=0, sticky=tk.E, pady=2)
        self.phone_number_entry.grid(row=3, column=1, columnspan=2, sticky=tk.W+tk.E, pady=2)
        self.phone_number_var.set(self.login_info.get("phone_number", ""))
        self.form_warning_lbl.grid(row=4, column=1, sticky=tk.W, pady=2)
        self.form_warning_var.set('')
        if origin == "choose info":
            self.form_back_btn.grid(row=5, column=2, sticky=tk.E, pady=(0, 10))
            self.form_back_btn.configure(state=tk.ACTIVE)
        self.save_button.grid(row=5, column=1, sticky=tk.E, pady=(0, 10))
        self.save_button.configure(state=tk.ACTIVE)
        self.update_idletasks()
        self.form_warning_lbl.configure(wraplength=self.winfo_width() - 100)

        self.parent.after(100, self.process_folder_queue())

    def check_credentials(self, call_origin):
        if call_origin == "choose info":
            self.saved_info_btn.configure(state=tk.DISABLED)
            self.update_info_btn.configure(state=tk.DISABLED)
            self.warning_lbl_style.configure("Warning.TLabel", foreground='green')
            self.choose_info_warning_var.set("Checking if saved password is still valid...")

        if call_origin == "save details":
            email = self.email_entry.get()
            password = self.password_entry.get()
            phone_number = self.phone_number_entry.get()
            try:
                if phone_number != '': int(phone_number.replace("+", "").replace(" ", "").replace("-", ""))
            except ValueError:
                self.warning_lbl_style.configure("Warning.TLabel", foreground='red')
                self.form_warning_var.set("Phone number must only contain numbers")
                self.phone_number_var.set('')
                self.phone_number_entry.focus()
                return
            if email != '' and password != '':
                if call_origin == "save details":
                    self.warning_lbl_style.configure("Warning.TLabel", foreground='green')
                    self.form_warning_var.set("Trying to log into your WG-Gesucht account...")
                    self.form_back_btn.configure(state=tk.DISABLED)
                    self.save_button.configure(state=tk.DISABLED)
                    self.login_info["email"] = email
                    self.login_info["password"] = password
                    self.login_info["phone_number"] = phone_number

            else:
                self.warning_lbl_style.configure("Warning.TLabel", foreground='red')
                self.form_warning_var.set("One or more fields are empty!")
                self.email_entry.focus()
                return
        cred_check_thread = threading.Thread(target=wg_gesucht.check_wg_credentials,
                                             args=[self.login_info, self.check_credentials_queue, call_origin])
        cred_check_thread.daemon = True
        cred_check_thread.start()
        self.parent.after(100, self.process_cred_queue())

    def check_credentials_return(self, status):
        if status == "save details ok":
            with open('.data_files/.login_info.json', 'w', encoding='utf-8') as save:
                json.dump(self.login_info, indent=4, sort_keys=True, fp=save)
                self.log_window("save details")
        elif status == "save details not ok":
            self.form_back_btn.configure(state=tk.ACTIVE)
            self.save_button.configure(state=tk.ACTIVE)
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus()
            self.form_warning_var.set("Could not sign into WG-Gesucht.de with the password you provided, "
                                      "please try again.")
        elif status == "save details no connection":
            self.form_warning_var.set("Could not connect to the internet, please check your connection and try again")
            self.form_back_btn.configure(state=tk.ACTIVE)
            self.save_button.configure(state=tk.ACTIVE)
        elif status == "save details timed out":
            self.form_warning_var.set("WG-Gesucht website timed out, please try again later")

    def log_window(self, origin):
        if origin == "choose info":
            self.choose_info_btn_frame.grid_forget()
        elif origin == "save details":
            self.form_frame.grid_forget()

        self.log_restart_button.grid_forget()
        self.log_back_button.grid_forget()

        self.stop_restart_frame.grid(row=1, column=0, padx=20, sticky=tk.W+tk.E)
        self.log_frame.grid(row=2, column=0, padx=20, pady=10, sticky=tk.W+tk.E)
        self.log_stop_button.grid(row=0, column=0, sticky=tk.W)
        self.log_text.grid(row=0, column=0, sticky=tk.W+tk.E)

        self.main_process.daemon = True
        self.main_process.start()
        self.parent.after(100, self.process_log_output_queue())

    def stop(self):
        pid = self.main_process.pid
        self.main_process.terminate()
        for process in psutil.process_iter():
            if process.pid == pid:
                process.kill()
        self.main_process = multiprocessing.Process(target=wg_gesucht.start_searching,
                                                    args=[self.login_info, self.log_output_queue, self.wg_ad_links,
                                                          self.offline_ad_links])
        self.log_stop_button.grid_forget()
        self.log_restart_button.grid(row=0, column=0, sticky=tk.W)
        self.log_back_button.grid(row=0, column=1, sticky=tk.W)
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, '\n')
        self.log_text.configure(state=tk.DISABLED)
        self.log_text.see(tk.END)

    def process_cred_queue(self):
        try:
            message = self.check_credentials_queue.get(0)
            if message == "login ok save details":
                self.check_credentials_return("save details ok")
            elif message == "login not ok save details":
                self.check_credentials_return("save details not ok")
            elif message == "timed out save details":
                self.check_credentials_return("save details timed out")
            elif message == "no connection save details":
                self.check_credentials_return("save details no connection")
            elif message == "no connection choose info":
                messagebox.showerror("No Connection!", "Could not connect to the internet, please check your "
                                                       "connection and try again", parent=self.parent)
                self.saved_info_btn.configure(state=tk.ACTIVE)
                self.update_info_btn.configure(state=tk.ACTIVE)
                self.choose_info_warning_var.set('')
            elif message == "timed out choose info":
                messagebox.showerror("Timed Out!", "WG-Gesucht website timed out, please try again later.",
                                     parent=self.parent)
                self.saved_info_btn.configure(state=tk.ACTIVE)
                self.update_info_btn.configure(state=tk.ACTIVE)
                self.choose_info_warning_var.set('')
            elif message == "login ok choose info":
                self.log_window("choose info")
            elif message == "login not ok choose info":
                messagebox.showerror("Password failed!", "Signing into WG-Gesucht.de failed with the password you saved"
                                                         " previously, if you changed the password on your "
                                                         "WG-Gesucht account, please save it here as well and try "
                                                         "again.", parent=self.parent)
                self.save_login_details("choose info")
                self.save_button.configure(state=tk.ACTIVE)
            self.parent.after(100, self.process_cred_queue)
        except queue.Empty:
            self.parent.after(100, self.process_cred_queue)

    def process_log_output_queue(self):
        try:
            message = self.log_output_queue.get(0)
            if message == "timed out running":
                self.stop()
                messagebox.showerror("Timed Out!", "WG-Gesucht website is not responding and has timed out, please try "
                                                   "again later", parent=self.parent)
            elif message == "no connection running":
                self.stop()
                messagebox.showerror("No Connection!", "Could not connect to the internet, please check your "
                                                       "connection and try again", parent=self.parent)
            elif isinstance(message, list):
                self.log_text.configure(state=tk.NORMAL)
                self.log_text.insert(tk.END, message[1] + '\n')
                self.log_text.configure(state=tk.DISABLED)
                self.log_text.see(tk.END)
                self.stop()
            else:
                self.log_text.configure(state=tk.NORMAL)
                self.log_text.insert(tk.END, message + '\n')
                self.log_text.configure(state=tk.DISABLED)
                self.log_text.see(tk.END)
                self.parent.after(100, self.process_log_output_queue)
        except queue.Empty:
            self.parent.after(100, self.process_log_output_queue)

    def process_folder_queue(self):
        try:
            message = self.folder_queue.get(0)
            if isinstance(message, list):
                messagebox.showinfo("Folders Created", f"Two folders have been created, '{self.wg_ad_links}' contains "
                                                       "a 'csv' file which contains the URL's of the apartment ads the "
                                                       f"program has messaged for you, and '{self.offline_ad_links}' "
                                                       "contains a the actual ads, which can be viewed offline, in "
                                                       "case the submitter has removed the ad before you get chance to "
                                                       "look at it", parent=self.parent, type="ok")
            self.update_idletasks()
        except queue.Empty:
            self.parent.after(100, self.process_folder_queue)


def main():
    root = tk.Tk()
    if sys.platform == 'win32':
        root.wm_iconbitmap(".icons/wg_icon_dark.ico")
        root.wm_title("WG Finder")
    else:
        root.wm_title("")
    app = MainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
