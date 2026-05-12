import smbus
import time
import math
import json
import paho.mqtt.client as mqtt

# --- MQTT KONFIGURATION ---
MQTT_BROKER = "127.0.0.1"  # Der Broker läuft direkt auf dem Pi
MQTT_PORT = 1883
MQTT_TOPIC = "home/sensors/gy511"

# --- I2C KONFIGURATION ---
BUS_NUMBER = 3
MAG_ADDRESS = 0x1E  # Magnetometer
ACC_ADDRESS = 0x19  # Beschleunigungssensor

# Register Magnetometer
CRA_REG_M = 0x00
CRB_REG_M = 0x01
MR_REG_M = 0x02
OUT_X_H_M = 0x03 

# Register Accelerometer
CTRL_REG1_A = 0x20
CTRL_REG4_A = 0x23
OUT_X_L_A = 0x28 

# Bus initialisieren
bus = smbus.SMBus(BUS_NUMBER)

def init_sensors():
    """Weckt beide Sensoren auf und konfiguriert sie."""
    # 1. Magnetometer (15 Hz, kontinuierlich)
    bus.write_byte_data(MAG_ADDRESS, CRA_REG_M, 0x10)
    bus.write_byte_data(MAG_ADDRESS, CRB_REG_M, 0x20)
    bus.write_byte_data(MAG_ADDRESS, MR_REG_M, 0x00)

    # 2. Beschleunigungssensor (100 Hz, alle Achsen aktiv)
    bus.write_byte_data(ACC_ADDRESS, CTRL_REG1_A, 0x57)
    # High-Resolution Modus, +/- 2g Messbereich
    bus.write_byte_data(ACC_ADDRESS, CTRL_REG4_A, 0x08)

def read_raw_mag(addr):
    """Liest das Magnetometer (High-Byte zuerst)"""
    high = bus.read_byte_data(MAG_ADDRESS, addr)
    low = bus.read_byte_data(MAG_ADDRESS, addr + 1)
    value = (high << 8) | low
    if value >= 32768:
        value = value - 65536
    return value

def read_raw_acc(addr):
    """Liest das Accelerometer (Low-Byte zuerst)"""
    low = bus.read_byte_data(ACC_ADDRESS, addr)
    high = bus.read_byte_data(ACC_ADDRESS, addr + 1)
    value = (high << 8) | low
    if value >= 32768:
        value = value - 65536
    
    # Der LSM303 liefert 12-Bit Werte, linksbündig. 
    # Wir müssen also durch 16 teilen (entspricht einem Bitshift >> 4)
    return value / 16.0

def get_sensor_data():
    """Liest alle Werte aus und berechnet sie."""
    # --- 1. Magnetometer (Winkel) ---
    # Register-Reihenfolge beim LSM303DLHC ist zwingend X, Z, Y!
    mag_x = read_raw_mag(OUT_X_H_M)
    
    # WICHTIG: Z-Achse auslesen, um den internen Register-Lock des Chips zu lösen!
    mag_z = read_raw_mag(OUT_X_H_M + 2) 
    
    mag_y = read_raw_mag(OUT_X_H_M + 4)
    
    # Winkel berechnen (Z wird hierfür nicht benötigt)
    heading_rad = math.atan2(mag_y, mag_x)
    heading_deg = math.degrees(heading_rad)
    if heading_deg < 0:
        heading_deg += 360

    # --- 2. Beschleunigung ---
    # Register-Reihenfolge ist X, Y, Z
    acc_x_raw = read_raw_acc(OUT_X_L_A)
    acc_y_raw = read_raw_acc(OUT_X_L_A + 2)
    acc_z_raw = read_raw_acc(OUT_X_L_A + 4)

    acc_x = acc_x_raw * 0.001
    acc_y = acc_y_raw * 0.001
    acc_z = acc_z_raw * 0.001

    return {
        "heading": round(heading_deg, 1),
        "accel_x": round(acc_x, 3),
        "accel_y": round(acc_y, 3),
        "accel_z": round(acc_z, 3)
    }

# --- Hauptprogramm ---
def main():
    print("Initialisiere GY-511 Sensoren...")
    init_sensors()
    
    client = mqtt.Client(client_id="Pi_GY511")
    print("Verbinde mit MQTT Broker auf localhost...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    print("Verbunden! Sende Daten... (Abbruch mit STRG+C)")
    print("-" * 50)

    try:
        while True:
            # Daten lesen und formatieren
            data = get_sensor_data()
            payload = json.dumps(data)
            
            # An Home Assistant senden
            client.publish(MQTT_TOPIC, payload)
            
            print(f"Gesendet: {payload}")
            time.sleep(0.5) # Alle 0.5 Sekunden ein Update
            
    except KeyboardInterrupt:
        print("\nSkript beendet.")
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        print(f"\nFehler: {e}")

if __name__ == "__main__":
    main()
    