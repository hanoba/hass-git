import smbus
import time

# I2C Adresse des ADS1115 (Standard: 0x48)
ADC_ADDR = 0x48

# Register Adressen
ADC_REG_CONVERSION = 0x00
ADC_REG_CONFIG     = 0x01

# Konfiguration (16-Bit) - Hex: 0xC183
# Bit 15:    1    -> Startet eine Einzelschuss-Messung
# Bit 14-12: 100  -> Eingang wählen (A0 gegen GND)
#            101  -> A1 gegen GND
#            110  -> A2 gegen GND
#            111  -> A3 gegen GND
# Bit 11-9:  000  -> Gain (+/- 6.144V)
# Bit 8:     1    -> Modus (Power-down / Single-Shot)
# Bit 7-5:   100  -> Datenrate (128 Samples per Second)
# Bit 4-0:   00011-> Komparator deaktiviert (Standard)
ADC_CONFIG = 0xC183 

# I2C-Bus 1 initialisieren (wird für Raspberry Pi typischerweise verwendet)
bus = smbus.SMBus(1)

def read_ads1115(channel):
    assert 0 <= channel <= 3, f"Channel out of range: {channel}. Must be between 0 and 3."
    config = ADC_CONFIG | (channel << 12)
    
    # 1. Konfiguration schreiben (Big-Endian: High-Byte zuerst)
    config_bytes = [(config >> 8) & 0xFF, config & 0xFF]
    bus.write_i2c_block_data(ADC_ADDR, ADC_REG_CONFIG, config_bytes)
    
    # 2. Warten, bis die Konvertierung abgeschlossen ist.
    time.sleep(0.01) 
    
    # 3. Ergebnis aus dem Conversion Register lesen (2 Bytes)
    res = bus.read_i2c_block_data(ADC_ADDR, ADC_REG_CONVERSION, 2)
    
    # 4. Bytes zusammenfügen (Big-Endian)
    raw_value = (res[0] << 8) | res[1]
    
    # 5. Zweierkomplement für negative Werte anwenden (16-Bit)
    if raw_value > 32767:
        raw_value -= 65536
        
    # 6. Umrechnung in Spannung (bei Gain +/- 6.144V)
    voltage = raw_value * (6.144 / 32768.0)
    
    return raw_value, voltage

# Hauptschleife
try:
    print("Starte Messung... (Abbruch mit STRG+C)")
    print("-" * 40)
    
    while True:
        raw, volt = read_ads1115()
        print(f"Rohwert: {raw:>6d} | Spannung: {volt:>7.4f} V")
        
        # Pause zwischen den Messungen
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nMessung durch Benutzer beendet.")

finally:
    # Den Bus am Ende sauber schließen, um Ressourcen freizugeben
    bus.close()
    print("I2C-Bus geschlossen.")