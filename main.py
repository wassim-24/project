import tkinter as tk
from tkinter import ttk
import RPi.GPIO as GPIO
from PIL import Image, ImageTk
from hardware import TCA9548A,MCP23017

# Set the GPIO mode to BCM (Broadcom SOC channel)
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

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
    # Replace with the actual GPIO pin number you are using
    COM_PIN = -1
    GND_PINS = [2, 3, 4, 14, 15, 17, 18, 27, 22, 23, 24, 10, 9, 25, 11, 8, 7, 5, 6, 12, 13, 19, 16, 26, 20, 21]
    GPIO.setup(2, GPIO.OUT)
    GPIO.output(2, GPIO.LOW)
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
        self.TCA = TCA9548A(bus)
        self.MCP = MCP23017(bus)

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
        self.login_error_label = tk.Label(self.login_frame, text="Invalid username or password", fg="red", bg="#1E1E1E")
        self.login_error_label.grid(row=3, columnspan=2, pady=5)

    def create_main_ui(self):
        self.master.title("Pattern Information Extractor")
        self.master.configure(bg="#1E1E1E")
        self.master.attributes("-fullscreen", True)
        # Logout Button
        logout_button = tk.Button(self.master, text="Logout", command=self.logout, bg="#F44336", fg="white", font=("Arial", 16), padx=10)
        logout_button.pack(anchor=tk.NE, padx=10, pady=10)

        company_label = tk.Label(self.master, text="NEXANS Autoelectric", bg="#1E1E1E", fg="white", font=("Helvetica", 20, "bold"))
        company_label.pack(anchor=tk.CENTER, padx=10, pady=(0, 5))
        # Label to display the logged-in user
        self.logged_in_user_label = tk.Label(self.master, text="", bg="#1E1E1E", fg="white", font=("Arial", 12))
        self.logged_in_user_label.pack(anchor=tk.NE, padx=10, pady=(0, 5))

        # QR Code Input
        qr_frame = tk.Frame(self.master)
        qr_frame.pack(pady=10)
        self.qr_code_label = tk.Label(qr_frame, text="QR Code:", font=("Helvetica", 18, "bold"), fg="black")
        self.qr_code_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)

        self.qr_code_entry = tk.Entry(qr_frame, width=40, font=("Helvetica", 16))  # Adjust width as needed
        self.qr_code_entry.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.qr_code_entry.insert(0, "CbTp0002Dc08LoCoCoCoSlCpCvSe")

        # Update button
        self.update_button = tk.Button(qr_frame, text="Extract Data", command=self.extract_and_update_data, bg="#4CAF50", fg="white", font=("Arial", 16), padx=10)
        self.update_button.grid(row=0, column=2, padx=(20, 10), sticky="w")  # Adjust padx for spacing

        # Close Button
        close_button = tk.Button(qr_frame, text="Close", command=self.close_window, bg="#F44336", fg="white", font=("Arial", 16), padx=10)
        close_button.grid(row=0, column=3, padx=(10, 20), sticky="w")  # Adjust padx for spacing

        # Create a frame for the table
        self.table_frame = ttk.Frame(self.master)
        self.table_frame.pack(fill=tk.BOTH, expand=True)

        # Add a canvas for scrolling
        self.canvas = tk.Canvas(self.table_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add a scrollbar
        self.scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.config(yscrollcommand=self.scrollbar.set)

        # Create another frame to contain the table
        self.table_container = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.table_container, anchor="nw")
        self.table_container.configure(width=800, height=400)  # Added here

        # Configure canvas scrolling
        self.table_container.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self.update_canvas_width)

        self.create_table()

    def logout(self):
        # Destroy main UI and recreate the login UI
        self.master.destroy()
        root = tk.Tk()
        app = PatternInfoExtractorApp(root)
        root.mainloop()

    def close_window(self):
        self.master.destroy()

    def create_table(self):
        # Table header
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

        # Clear existing rows
        for widget in self.table_container.winfo_children():
            widget.destroy()

        self.create_table()

        # Add Switch Row
        self.add_table_row("1", "LED", "", "LED", 1)

        # Add Pins Rows
        for i in range(1, n_pins + 1):
            self.add_table_row(f" {i + 1}", f"PIN {i}", "Not Yet", "PIN", i + 1)

        # Add Common Conditions Row
        self.add_table_row(f" {n_pins + 2}", f"COM", "PIN ON" if self.isOpen else "PIN OFF", "COM", n_pins + 2)

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

        else: # Create a switch
            switch_state = tk.BooleanVar()
            switch_state.set(False)  # Set initial state

            # Load images for switches
            on_image = Image.open(("/home/pi/Images/closed.jpg"))
            off_image = Image.open(("/home/pi/Images/open.jpg"))

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
                if 1 <= self.COM_PIN <= 27:  # Assuming valid GPIO channels are 1 to 27
                    GPIO.setup(self.COM_PIN, GPIO.OUT)
                    GPIO.output(self.COM_PIN, GPIO.LOW)
                    print("COM ON" + str(self.COM_PIN))
            else:
                if 1 <= self.COM_PIN <= 27:  # Assuming valid GPIO channels are 1 to 27
                    GPIO.setup(self.COM_PIN, GPIO.OUT)
                    GPIO.output(self.COM_PIN, GPIO.HIGH)
                    print("COM OFF" + str(self.COM_PIN))
                self.COM_PIN = -1
            label_col1.configure(bg='#FFE599', font=("Helvetica", 16))
            label_col2.configure(bg='#FFE599', font=("Helvetica", 16))

    def update_canvas_width(self, event):
        pass

    def toggle_start(self):
        self.isOpen = not self.isOpen
        if self.isOpen:
            # Set up GPIO pins for GND detection
            for pin in self.GND_PINS:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(pin, GPIO.BOTH, callback=self.detect_gnd_connection, bouncetime=5)
        else:
            # Remove event detection for GND pins
            for pin in self.GND_PINS:
                GPIO.remove_event_detect(pin)

        self.extract_and_update_data()

    def detect_gnd_connection(self, channel):
        print("GND connection detected on pin", channel)
        if GPIO.input(channel) == GPIO.LOW:
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
                "Ad": "Addional Part"
        }
        return condition_map.get(code, "Unknown")



if __name__ == "__main__":
    root = tk.Tk()
    app = PatternInfoExtractorApp(root)
    root.mainloop()
    GPIO.cleanup()
