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
ADC_ADDRESS = 0x48  # ADS1115 (Standard: 0x48)

# Register Magnetometer
CRA_REG_M = 0x00
CRB_REG_M = 0x01
MR_REG_M = 0x02
OUT_X_H_M = 0x03 

# Register Accelerometer
CTRL_REG1_A = 0x20
CTRL_REG4_A = 0x23
OUT_X_L_A = 0x28 

# ADS1115 Register Adressen
ADC_REG_CONVERSION = 0x00
ADC_REG_CONFIG     = 0x01

# Konfiguration (16-Bit) - Hex: 0xC183
# Bit 15:    1    -> Startet eine Einzelschuss-Messung
# Bit 14-12: 100  -> Eingang wählen (A0 gegen GND)
#            101  -> A1 gegen GND
#            110  -> A2 gegen GND
#            111  -> A3 gegen GND
# Bit 11-9:  000  -> Gain (+/- 6.144V, 187.5uV)
#            001  -> +/- 4.096V, 125.0uV
# Bit 8:     1    -> Modus (Power-down / Single-Shot)
# Bit 7-5:   100  -> Datenrate (128 Samples per Second)
# Bit 4-0:   00011-> Komparator deaktiviert (Standard)
ADC_CONFIG = 0xC383 
ADC_FACTOR = (4.096 / 32768.0) * 14.1 / 13.8240
AdcFactor = [ADC_FACTOR, ADC_FACTOR, ADC_FACTOR*6, ADC_FACTOR*6*11.98/12.10]

# Bus initialisieren
bus = smbus.SMBus(BUS_NUMBER)

def read_ads1115(channel):
    assert 0 <= channel <= 3, f"Channel out of range: {channel}. Must be between 0 and 3."
    config = ADC_CONFIG | (channel << 12)
    
    # 1. Konfiguration schreiben (Big-Endian: High-Byte zuerst)
    config_bytes = [(config >> 8) & 0xFF, config & 0xFF]
    bus.write_i2c_block_data(ADC_ADDRESS, ADC_REG_CONFIG, config_bytes)
    
    # 2. Warten, bis die Konvertierung abgeschlossen ist.
    time.sleep(0.01) 
    
    # 3. Ergebnis aus dem Conversion Register lesen (2 Bytes)
    res = bus.read_i2c_block_data(ADC_ADDRESS, ADC_REG_CONVERSION, 2)
    
    # 4. Bytes zusammenfügen (Big-Endian)
    raw_value = (res[0] << 8) | res[1]
    
    # 5. Zweierkomplement für negative Werte anwenden (16-Bit)
    if raw_value > 32767:
        raw_value -= 65536
        
    # 6. Umrechnung in Spannung (bei Gain +/- 6.144V)
    voltage = raw_value * AdcFactor[channel]
    
    return voltage

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

    x_neigung = math.degrees(math.atan2(acc_x_raw, acc_z_raw))
    y_neigung = math.degrees(math.atan2(acc_y_raw, acc_z_raw))
    
    #acc_x = acc_x_raw * 0.001
    #acc_y = acc_y_raw * 0.001
    #acc_z = acc_z_raw * 0.001
    
    fs = read_ads1115(1)
    vin1 = read_ads1115(2)
    vin2 = read_ads1115(3)

    return {
        "heading": int(round(heading_deg, 0)),
        "x_neigung": round(x_neigung, 1),
        "y_neigung": round(y_neigung, 1),
        "fs": round(fs, 1),
        "vin1": round(vin1, 1),
        "vin2": round(vin2, 1),
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
    