import smbus2
import time

# Constants for I2C addresses
TCA9548A_ADDR = 0x70  # Default I2C address for TCA9548A
MCP23017_ADDR_BASE = 0x20  # Base I2C address for MCP23017

# I2C bus number (usually 1 for Raspberry Pi)
I2C_BUS = 1
RETRY_COUNT = 5
RETRY_DELAY = 0.5  # Increased delay in seconds between retries
CONFIG_DELAY = 1   # Delay after configuring MCP23017
SCAN_DELAY = 10    # Delay in seconds between each scan cycle

class TCA9548A:
    def __init__(self, bus, address=0x70):
        self.bus = bus
        self.address = address

    def select_all_channels(self):
        for attempt in range(RETRY_COUNT):
            try:
                self.bus.write_byte(self.address, 0xFF)  # Enable all channels
                selected = self.bus.read_byte(self.address)
                if selected == 0xFF:
                    print("All channels selected.")
                    return
                else:
                    print(f"Attempt {attempt + 1}: Failed to select all channels. Selected: {selected:#04x}")
            except OSError as e:
                print(f"Attempt {attempt + 1}: Error selecting all channels: {e}")
            time.sleep(RETRY_DELAY)

        print("Failed to select all channels after retries.")

class MCP23017:
    def __init__(self, bus, address):
        self.bus = bus
        self.address = address

    def configure_as_inputs_with_pullups(self):
        for attempt in range(RETRY_COUNT):
            try:
                # Set all pins on both GPIOA and GPIOB as inputs (IODIRA and IODIRB)
                self.bus.write_byte_data(self.address, 0x00, 0xFF)  # IODIRA register
                self.bus.write_byte_data(self.address, 0x01, 0xFF)  # IODIRB register
                # Enable pull-up resistors on all pins (GPPUA and GPPUB)
                self.bus.write_byte_data(self.address, 0x0C, 0xFF)  # GPPUA register
                self.bus.write_byte_data(self.address, 0x0D, 0xFF)  # GPPUB register

                # Verify configuration
                iodira = self.bus.read_byte_data(self.address, 0x00)
                iodirb = self.bus.read_byte_data(self.address, 0x01)
                gppua = self.bus.read_byte_data(self.address, 0x0C)
                gppub = self.bus.read_byte_data(self.address, 0x0D)

                if iodira == 0xFF and iodirb == 0xFF and gppua == 0xFF and gppub == 0xFF:
                    print(f"Configured IODIRA: {iodira:#04x}, IODIRB: {iodirb:#04x}")
                    print(f"Configured GPPUA: {gppua:#04x}, GPPUB: {gppub:#04x}")
                    return
                else:
                    print(f"Attempt {attempt + 1}: Failed to configure MCP23017 at address {self.address:#02x}")

            except OSError as e:
                print(f"Attempt {attempt + 1}: Error configuring MCP23017 at address {self.address:#02x}: {e}")
            time.sleep(RETRY_DELAY)

        print(f"Failed to configure MCP23017 at address {self.address:#02x} after retries.")

    def is_connected(self):
        for attempt in range(RETRY_COUNT):
            try:
                # Attempt to read IODIRA register (0x00)
                self.bus.read_byte_data(self.address, 0x00)
                return True
            except OSError:
                time.sleep(RETRY_DELAY)
        return False

    def read_gpio(self):
        for attempt in range(RETRY_COUNT):
            try:
                gpioa = self.bus.read_byte_data(self.address, 0x12)  # GPIOA register
                gpiob = self.bus.read_byte_data(self.address, 0x13)  # GPIOB register
                return gpioa, gpiob
            except OSError as e:
                print(f"Attempt {attempt + 1}: Error reading GPIO from MCP23017 at address {self.address:#02x}: {e}")
                time.sleep(RETRY_DELAY)
        return None, None

    def write_gpio(self, port, value):
        reg = 0x14 if port == 'A' else 0x15  # OLATA or OLATB
        for attempt in range(RETRY_COUNT):
            try:
                self.bus.write_byte_data(self.address, reg, value)
                return True
            except OSError as e:
                print(f"Attempt {attempt + 1}: Error writing GPIO to MCP23017 at address {self.address:#02x}: {e}")
                time.sleep(RETRY_DELAY)
        return False

def main():
    try:
        bus = smbus2.SMBus(I2C_BUS)
    except FileNotFoundError as e:
        print(f"Error: Could not open I2C bus: {e}")
        return

    tca = TCA9548A(bus, TCA9548A_ADDR)
    tca.select_all_channels()  # Enable all channels at once
    mcp_addresses = [MCP23017_ADDR_BASE + i for i in range(8)]  # Possible addresses for MCP23017

    try:
        while True:
            connected_devices = []

            for addr in mcp_addresses:
                mcp = MCP23017(bus, addr)
                if mcp.is_connected():
                    connected_devices.append(addr)
                    print(f"Found MCP23017 at address 0x{addr:02X}")
                    mcp.configure_as_inputs_with_pullups()  # Ensure proper configuration
                    time.sleep(CONFIG_DELAY)  # Add delay after configuration

            print("\nSummary of connected MCP23017 devices:")
            for addr in connected_devices:
                print(f"MCP23017 at address 0x{addr:02X}")
                mcp = MCP23017(bus, addr)
                mcp.configure_as_inputs_with_pullups()  # Reconfigure before reading
                time.sleep(CONFIG_DELAY)  # Add delay before reading
                gpioa, gpiob = mcp.read_gpio()
                if gpioa is not None and gpiob is not None:
                    print(f"  Raw GPIOA: {gpioa:#04x}, Raw GPIOB: {gpiob:#04x}")
                    for pin in range(8):
                        if not (gpioa & (1 << pin)):  # Check each pin of GPIOA
                            print(f"  GND detected at pin A{pin} in MCP23017 at address 0x{addr:02X}.")
                    for pin in range(8):
                        if not (gpiob & (1 << pin)):  # Check each pin of GPIOB
                            print(f"  GND detected at pin B{pin} in MCP23017 at address 0x{addr:02X}.")

                    # Example write operation to GPIOA
                    if mcp.write_gpio('A', 0xFF):
                        print(f"  Successfully wrote to GPIOA in MCP23017 at address 0x{addr:02X}.")
                    else:
                        print(f"  Failed to write to GPIOA in MCP23017 at address 0x{addr:02X}.")

            time.sleep(SCAN_DELAY)  # Delay between scans to avoid overwhelming the I2C bus

    except KeyboardInterrupt:
        print("Stopping the scan.")
    finally:
        bus.close()

if __name__ == "__main__":
    main()
