import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import smbus2
from hardware import TCA9548A
from hardware import MCP23017

class PatternInfoExtractorApp:
    # Define user credentials
    USERS = {
        "gam": "abdelaziz",
        "a": "111",
        "Nsir Wassim": "12345678",
        # Add more users as needed
    }
    I2C_BUS = 1
    isOpen = False
    # Define MCP23017 addresses
    MCP_ADDRESS = 0x20
    TCA_ADDRESS = 0x70
    
    COM_PIN = -1
    GND_PINS = list(range(16))  # MCP23017 has 16 pins, indexed 0-15
    
    bus = smbus2.SMBus(I2C_BUS)
    
    def __init__(self, master):
        self.master = master
        self.on_image_tk = None  # Define on_image_tk attribute
        self.off_image_tk = None  # Define off_image_tk attribute
        self.login_frame = tk.Frame(master)
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self.logged_in = False
        self.logged_in_user_label = tk.Label(self.master, text="", bg="#1E1E1E", fg="white", font=("Arial", 12))
        self.logged_in_user_label.pack(anchor=tk.W, padx=0, pady=(0, 0))
        self.create_login_ui()
        self.TCA = TCA9548A(self.bus)
        self.MCP = MCP23017(self.bus, self.MCP_ADDRESS)  # Pass the address directly

    def create_login_ui(self):
        self.master.title("Connexion")
        self.login_frame.configure(bg="#1E1E1E")
        self.label_username = tk.Label(self.login_frame, text="Username:", bg="#1E1E1E", fg="white", anchor=tk.CENTER)
        self.label_password = tk.Label(self.login_frame, text="Password:", bg="#1E1E1E", fg="white", anchor=tk.CENTER)
        self.entry_username = tk.Entry(self.login_frame)
        self.entry_password = tk.Entry(self.login_frame, show="*")

        self.label_username.grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.label_password.grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        self.entry_username.grid(row=0, column=1, padx=5, pady=5)
        self.entry_password.grid(row=1, column=1, padx=5, pady=5)

        self.button_login = tk.Button(self.login_frame, text="Login", command=self.login, bg="#4CAF50", fg="white", font=("Arial", 16), padx=10)
        self.button_login.grid(row=2, columnspan=2, pady=10)

    def login(self):
        username = self.entry_username.get()
        password = self.entry_password.get()

        # Check if username and password are correct
        if username in self.USERS and self.USERS[username] == password:
            self.logged_in = True
            self.logged_in_user_label.config(text=f"Logged in as: {username}")
            self.login_frame.destroy()  # Close login UI
            self.create_main_ui()
        else:
            self.show_login_error()

    def show_login_error(self):
        # Delete any existing error label
        if hasattr(self, "login_error_label"):
            self.login_error_label.destroy()

        # Show login error label
        self.login_error_label = tk.Label(self.login_frame, text="Invalid username or password", fg="red", bg="#1E1E1E", anchor=tk.CENTER)
        self.login_error_label.grid(row=3, columnspan=2, padx=5, pady=5)

    def create_main_ui(self):
        self.master.geometry("1000x700")
        self.master.title("Pattern Info Extractor")
        self.main_frame = tk.Frame(self.master, bg="#1E1E1E")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.main_frame, bg="#1E1E1E")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.table_container = tk.Frame(self.canvas, bg="#1E1E1E")
        self.canvas.create_window((0, 0), window=self.table_container, anchor=tk.NW)
        self.table_container.bind("<Configure>", self.update_canvas_width)

        self.extract_and_update_data()

    def extract_and_update_data(self):
        self.table_container.destroy()
        self.table_container = tk.Frame(self.canvas, bg="#1E1E1E")
        self.canvas.create_window((0, 0), window=self.table_container, anchor=tk.NW)
        self.table_container.bind("<Configure>", self.update_canvas_width)

        num_rows = 5  # Example number of rows
        n_pins = 4
        n_cdns = 5
        cdn_array = ["Lo", "Co", "Sl", "Cl", "Cp"]

        # Add the header row
        self.add_table_row("Pin No.", "Function", "Status", "Type", 0)

        # Add pin rows
        for i in range(1, n_pins + 1):
            self.add_table_row(f"{i}", f"Pin {i}", "OFF", "PIN", i)

        # Add COM pin row
        self.add_table_row(f"{n_pins + 2}", "COM", "PIN ON" if self.isOpen else "PIN OFF", "COM", n_pins + 2)

        # Add other Conditions Rows
        for i in range(1, n_cdns + 1):
            condition_name = self.get_condition_name(cdn_array[i - 1])
            self.add_table_row(f"{n_pins + 2 + i}", condition_name, "Not Yet", "CDN", n_pins + 2 + i)

    def add_table_row(self, col1, col2, status, typ, pin_number):
        row_index = len(self.table_container.winfo_children()) // 3  # 3 columns
        self.table_container.columnconfigure(1, weight=1)
        # Create labels for the first two columns
        # Column One
        label_col1 = tk.Label(self.table_container, text=col1, font=("Helvetica", 16))
        label_col1.grid(row=row_index, column=0, padx=5, pady=5)
        # Column Two
        label_col2 = tk.Label(self.table_container, text=col2, font=("Helvetica", 16))
        label_col2.grid(row=row_index, column=1, padx=5, pady=5)

        if col1 == "1":
            run_and_stop = tk.Button(self.table_container, text='STOP' if self.isOpen else 'START', command=self.toggle_start, bg="#FF0000" if self.isOpen else "#00FF00", fg="white", font=("Arial", 16), padx=10)
            run_and_stop.grid(row=row_index, column=2, padx=5, pady=5)

        else:  # Create a switch
            switch_state = tk.BooleanVar()
            switch_state.set(False)  # Set initial state

            # Load images for switches
            on_image = Image.open("closed.jpg")
            off_image = Image.open("open.jpg")

            # Resize images
            on_image = on_image.resize((100, 65), Image.LANCZOS)
            off_image = off_image.resize((100, 65), Image.LANCZOS)

            # Convert images to tkinter compatible format
            self.on_image_tk = ImageTk.PhotoImage(on_image)
            self.off_image_tk = ImageTk.PhotoImage(off_image)

            switch = tk.Label(self.table_container, image=self.off_image_tk, bg="#1E1E1E")
            switch.grid(row=row_index, column=2, padx=5, pady=5)

            # Toggle switch image based on switch state
            switch.config(image=self.on_image_tk if switch_state.get() else self.off_image_tk)
            switch.image = self.on_image_tk if switch_state.get() else self.off_image_tk
            switch_state.trace_add('write', lambda *args: switch.config(image=self.on_image_tk if switch_state.get() else self.off_image_tk))

        if typ == "COM":
            if self.isOpen:
                self.COM_PIN = pin_number
                self.MCP.write_gpio('A', 0x00)  # Turn on COM_PIN (using GPIOA for simplicity)
                print("COM ON" + str(self.COM_PIN))
            else:
                self.MCP.write_gpio('A', 0xFF)  # Turn off COM_PIN (using GPIOA for simplicity)
                print("COM OFF" + str(self.COM_PIN))
                self.COM_PIN = -1
            label_col1.configure(bg='#FFE599', font=("Helvetica", 16))
            label_col2.configure(bg='#FFE599', font=("Helvetica", 16))

    def update_canvas_width(self, event):
        pass

    def toggle_start(self):
        self.isOpen = not self.isOpen
        if self.isOpen:
            # Set up MCP23017 pins for GND detection
            self.MCP.configure_as_inputs_with_pullups()
        self.extract_and_update_data()

    def detect_gnd_connection(self, channel):
        print("GND connection detected on pin", channel)
        if self.MCP.read_gpio()[channel // 8] & (1 << (channel % 8)) == 0:
            # GND connection detected
            self.switch_on(channel)
        else:
            # No GND connection detected
            self.switch_off(channel)

    def switch_on(self, channel):
        row_index = channel   # Assuming pin numbers start from 1
        switch = self.table_container.grid_slaves(row=row_index, column=2)[0]  # Get the switch widget
        switch.config(image=self.on_image_tk)  # Update switch to show LED is ON

    def switch_off(self, channel):
        row_index = channel   # Assuming pin numbers start from 1
        switch = self.table_container.grid_slaves(row=row_index, column=2)[0]  # Get the switch widget
        switch.config(image=self.off_image_tk)  # Update switch to show LED is OFF

    def get_condition_name(self, code):
        # Map condition codes to full names
        condition_map = {
            "Lo": "Locking",
            "Co": "Coding",
            "Sl": "Seclock",
            "Cl": "Clips",
            "Cp": "Cpa",
            "Cv": "Cover",
            "Se": "Seal",
            "La": "Latch",
            "Ad": "Additional Part"
        }
        return condition_map.get(code, "Unknown")

if __name__ == "__main__":
    root = tk.Tk()
    app = PatternInfoExtractorApp(root)
    root.mainloop()
