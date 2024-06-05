import smbus2
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import RPi.GPIO as GPIO

# Set the GPIO mode to BCM (Broadcom SOC channel)
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Constants for I2C addresses
TCA9548A_ADDR = 0x70  # Default I2C address for TCA9548A
MCP23017_ADDR_BASE = 0x20  # Base I2C address for MCP23017

# I2C bus number (usually 1 for Raspberry Pi)
I2C_BUS = 1
RETRY_COUNT = 5
RETRY_DELAY = 0.5  # Delay in seconds between retries

class TCA9548A:
    def __init__(self, bus, address=TCA9548A_ADDR):
        self.bus = bus
        self.address = address

    def select_channel(self, channel):
        for attempt in range(RETRY_COUNT):
            try:
                self.bus.write_byte(self.address, 1 << channel)
                selected = self.bus.read_byte(self.address)
                if selected == (1 << channel):
                    return
            except OSError as e:
                time.sleep(RETRY_DELAY)
        print(f"Failed to select channel {channel} after retries.")

class MCP23017:
    def __init__(self, bus, address):
        self.bus = bus
        self.address = address

    def configure_as_inputs_with_pullups(self):
        for attempt in range(RETRY_COUNT):
            try:
                if(self.address == MCP23017_ADDR_BASE):
                    # Set all A pins as inputs except the first pin (A0), which is an output (0b11111110 = 0xFE)
                    self.bus.write_byte_data(self.address, 0x00, 0xFE)  # IODIRA register
                    self.bus.write_byte_data(self.address, 0x01, 0xFF)  # IODIRB register (all B pins as inputs)
                    # Enable pull-up resistors on all A and B pins
                    self.bus.write_byte_data(self.address, 0x0C, 0xFF)  # GPPUA register
                    self.bus.write_byte_data(self.address, 0x0D, 0xFF)  # GPPUB register
                else:
                    self.bus.write_byte_data(self.address, 0x00, 0xFF)  # IODIRA register
                    self.bus.write_byte_data(self.address, 0x01, 0xFF)  # IODIRB register
                    self.bus.write_byte_data(self.address, 0x0C, 0xFF)  # GPPUA register
                    self.bus.write_byte_data(self.address, 0x0D, 0xFF)  # GPPUB register
                    return
            except OSError as e:
                time.sleep(RETRY_DELAY)
        print(f"Failed to configure MCP23017 at address {self.address:#02x} after retries.")

    def is_connected(self):
        for attempt in range(RETRY_COUNT):
            try:
                self.bus.read_byte_data(self.address, 0x00)
                return True
            except OSError:
                time.sleep(RETRY_DELAY)
        return False

    def read_gpio(self):
        try:
            gpioa = self.bus.read_byte_data(self.address, 0x12)  # GPIOA register
            gpiob = self.bus.read_byte_data(self.address, 0x13)  # GPIOB register
            return gpioa, gpiob
        except OSError as e:
            print(f"Error reading GPIO from MCP23017 at address {self.address:#02x}: {e}")
            return None, None
    def write_pin_high(self, pin):
        if pin < 8:
            current_state = self.bus.read_byte_data(self.address, 0x14)  # OLATA register
            new_state = current_state | (1 << pin)
            self.bus.write_byte_data(self.address, 0x14, new_state)
        else:
            current_state = self.bus.read_byte_data(self.address, 0x15)  # OLATB register
            new_state = current_state | (1 << (pin - 8))
            self.bus.write_byte_data(self.address, 0x15, new_state)

    def write_pin_low(self, pin):
        if pin < 8:
            current_state = self.bus.read_byte_data(self.address, 0x14)  # OLATA register
            new_state = current_state & ~(1 << pin)
            self.bus.write_byte_data(self.address, 0x14, new_state)
        else:
            current_state = self.bus.read_byte_data(self.address, 0x15)  # OLATB register
            new_state = current_state & ~(1 << (pin - 8))
            self.bus.write_byte_data(self.address, 0x15, new_state)

class PatternInfoExtractorApp:
    USERS = {
        "gam": "abdelaziz",
        "a": "111",
        "Nsir Wassim": "12345678",
        # Add more users as needed
    }

    def __init__(self, master):
        self.master = master
        self.isOpen = False  # Initialize isOpen attribute
        self.logged_in = False
        self.mcp_devices = []  # List to store MCP23017 instances
        self.on_image_tk = None
        self.off_image_tk = None
        self.switch_on_image_tk = None
        self.switch_off_image_tk = None
        self.login_frame = tk.Frame(master)
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self.logged_in_user_label = tk.Label(self.master, text="", bg="#1E1E1E", fg="white", font=("Arial", 12))
        self.logged_in_user_label.pack(anchor=tk.W, padx=0, pady=(0, 0))
        self.create_login_ui()

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
        if hasattr(self, "login_error_label"):
            self.login_error_label.destroy()

        self.login_error_label = tk.Label(self.login_frame, text="Invalid username or password", fg="red", bg="#1E1E1E")
        self.login_error_label.grid(row=3, columnspan=2, pady=5)

    def create_main_ui(self):
        self.master.title("Pattern Information Extractor")
        self.master.configure(bg="#1E1E1E")
        self.master.attributes("-fullscreen", True)
        logout_button = tk.Button(self.master, text="Logout", command=self.logout, bg="#F44336", fg="white", font=("Arial", 16), padx=10)
        logout_button.pack(anchor=tk.NE, padx=10, pady=10)

        company_label = tk.Label(self.master, text="NEXANS Autoelectric", bg="#1E1E1E", fg="white", font=("Helvetica", 20, "bold"))
        company_label.pack(anchor=tk.CENTER, padx=10, pady=(0, 5))

        self.logged_in_user_label = tk.Label(self.master, text="", bg="#1E1E1E", fg="white", font=("Arial", 12))
        self.logged_in_user_label.pack(anchor=tk.NE, padx=10, pady=(0, 5))

        qr_frame = tk.Frame(self.master)
        qr_frame.pack(pady=10)
        self.qr_code_label = tk.Label(qr_frame, text="QR Code:", font=("Helvetica", 18, "bold"), fg="black")
        self.qr_code_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)

        self.qr_code_entry = tk.Entry(qr_frame, width=40, font=("Helvetica", 16))
        self.qr_code_entry.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.qr_code_entry.insert(0, "CbTp0002Dc08LoCoCoCoSlCpCvSe")

        self.update_button = tk.Button(qr_frame, text="Extract Data", command=self.extract_and_update_data, bg="#4CAF50", fg="white", font=("Arial", 16), padx=10)
        self.update_button.grid(row=0, column=2, padx=(20, 10), sticky="w")

        close_button = tk.Button(qr_frame, text="Close", command=self.close_window, bg="#F44336", fg="white", font=("Arial", 16), padx=10)
        close_button.grid(row=0, column=3, padx=(10, 20), sticky="w")

        self.table_frame = ttk.Frame(self.master)
        self.table_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.table_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.config(yscrollcommand=self.scrollbar.set)

        self.table_container = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.table_container, anchor="nw")
        self.table_container.configure(width=800, height=400)

        self.table_container.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self.update_canvas_width)

        self.create_table()

        self.init_i2c_devices()

    def init_i2c_devices(self):
        try:
            self.bus = smbus2.SMBus(I2C_BUS)
            self.tca = TCA9548A(self.bus)
            for i in range(8):
                self.tca.select_channel(i)
                addr = MCP23017_ADDR_BASE + i
                mcp = MCP23017(self.bus, addr)
                if mcp.is_connected():
                    mcp.configure_as_inputs_with_pullups()
                    self.mcp_devices.append(mcp)
            if not self.isOpen: 
                self.mcp_devices[0].write_pin_high(0)
            else:
                self.mcp_devices[0].write_pin_low(0)   
        except Exception as e:
            print(f"Error initializing I2C devices: {e}")

    def logout(self):
        self.master.destroy()
        root = tk.Tk()
        app = PatternInfoExtractorApp(root)
        root.mainloop()

    def close_window(self):
        self.master.destroy()
        GPIO.cleanup()

    def create_table(self):
        columns = ["CODE", "DESCRIPTION", "STATUS"]
        for col_index, col_name in enumerate(columns):
            label = tk.Label(self.table_container, text=col_name, font=("Helvetica", 22, "bold"))
            label.grid(row=0, column=col_index, padx=250, pady=5)

    def extract_and_update_data(self):
        qr_value = self.qr_code_entry.get()
        pins_numbers = qr_value[4:8]
        conditions_numbers = qr_value[10:12]
        conditions_string = qr_value[12:]
        cdn_array = [conditions_string[i:i + 2] for i in range(0, len(conditions_string), 2)]

        n_pins = int(pins_numbers)
        n_cdns = int(conditions_numbers)

        for widget in self.table_container.winfo_children():
            widget.destroy()

        self.create_table()

        self.add_table_row("1", "LED", "", "LED", 1)

        for i in range(1, n_pins + 1):
            self.add_table_row(f" {i + 1}", f"PIN {i}", "Not Yet", "PIN", i + 1)

        self.add_table_row(f" {n_pins + 2}", f"COM", "PIN ON" if self.isOpen else "PIN OFF", "COM", n_pins + 2)

        for i in range(1, n_cdns + 1):
            condition_name = self.get_condition_name(cdn_array[i - 1])
            self.add_table_row(f"{n_pins + 2 + i}", condition_name, "Not Yet", "CDN", n_pins + 2 + i)

    def add_table_row(self, col1, col2, status, typ, pin_number):
        row_index = len(self.table_container.winfo_children()) // 3
        self.table_container.columnconfigure(1, weight=1)
        label_col1 = tk.Label(self.table_container, text=col1, font=("Helvetica", 16))
        label_col1.grid(row=row_index, column=0, padx=5, pady=5)
        label_col2 = tk.Label(self.table_container, text=col2, font=("Helvetica", 16))
        label_col2.grid(row=row_index, column=1, padx=5, pady=5)

        if col1 == "1":
            self.run_and_stop = tk.Button(self.table_container, text='STOP' if self.isOpen else 'START', command=self.toggle_start, bg="#FF0000" if self.isOpen else "#00FF00", fg="white", font=("Arial", 16), padx=10)
            self.run_and_stop.grid(row=row_index, column=2, padx=5, pady=5)
        else:
            switch_state = tk.BooleanVar()
            switch_state.set(False)

            on_image = Image.open("/home/pi/Images/closed.jpg")
            off_image = Image.open("/home/pi/Images/open.jpg")

            on_image = on_image.resize((100, 65), Image.LANCZOS)
            off_image = off_image.resize((100, 65), Image.LANCZOS)

            self.on_image_tk = ImageTk.PhotoImage(on_image)
            self.off_image_tk = ImageTk.PhotoImage(off_image)

            switch = tk.Label(self.table_container, image=self.off_image_tk, bg="#1E1E1E")
            switch.grid(row=row_index, column=2, padx=5, pady=5)

            switch.config(image=self.on_image_tk if switch_state.get() else self.off_image_tk)
            switch.image = self.on_image_tk if switch_state.get() else self.off_image_tk
            switch_state.trace_add('write', lambda *args: switch.config(image=self.on_image_tk if switch_state.get() else self.off_image_tk))

        if typ == "COM":
            self.COM_PIN = pin_number
            label_col1.configure(bg='#FFE599', font=("Helvetica", 16))
            label_col2.configure(bg='#FFE599', font=("Helvetica", 16))

    def update_canvas_width(self, event):
        pass

    def toggle_start(self):
        self.isOpen = not self.isOpen
        if not self.isOpen: 
            self.mcp_devices[0].write_pin_high(0)
        else:
            self.mcp_devices[0].write_pin_low(0)
        self.run_and_stop.config(text='STOP' if self.isOpen else 'START', bg="#FF0000" if self.isOpen else "#00FF00")
        if self.isOpen:
            self.detect_gnd_connections()
        else:
            self.master.after_cancel(self.detect_gnd_connections)

    def detect_gnd_connections(self):
        if self.isOpen:
            for channel in range(8):
                self.tca.select_channel(channel)
                for mcp in self.mcp_devices:
                    gpioa, gpiob = mcp.read_gpio()
                    if mcp.address == MCP23017_ADDR_BASE:
                        x = 1
                    else:
                        x = 0
                    if gpioa is not None and gpiob is not None:
                        for pin in range(x,8):
                            if not (gpioa & (1 << pin)):
                                self.switch_on(pin + 1 + channel * 16)
                            else:
                                self.switch_off(pin + 1 + channel * 16)
                            if not (gpiob & (1 << pin)):
                                self.switch_on(pin + 9 + channel * 16)
                            else:
                                self.switch_off(pin + 9 + channel * 16)
            self.master.after(1000, self.detect_gnd_connections)

    def switch_on(self, pin_number):
        row_index = pin_number + 1 # Assuming pin numbers start from 1
        try:
            switch = self.table_container.grid_slaves(row=row_index, column=2)[0]  # Get the switch widget
            switch.config(image=self.on_image_tk)  # Update switch to show LED is ON
        except IndexError:
            print(f"Switch at row {row_index} not found.")

    def switch_off(self, pin_number):
        row_index = pin_number + 1 # Assuming pin numbers start from 1
        try:
            switch = self.table_container.grid_slaves(row=row_index, column=2)[0]  # Get the switch widget
            switch.config(image=self.off_image_tk)  # Update switch to show LED is OFF
        except IndexError:
            print(f"Switch at row {row_index} not found.")

    def get_condition_name(self, code):
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
    try:
        root = tk.Tk()
        app = PatternInfoExtractorApp(root)
        root.mainloop()
    finally:
        GPIO.cleanup()
