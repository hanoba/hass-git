DEST=/home/harald/hass-git/config/
SERVICE=/etc/systemd/system/
HA=/home/harald/homeassistant/
# --checksum: rsync berechnet eine Prüfsumme (Hash) für die Quelldatei und die Zieldatei.
# Nur wenn diese Hashes unterschiedlich sind, wird die Datei überschrieben.
rsync --progress --checksum $SERVICE/gy511.service $DEST
rsync --progress --checksum $SERVICE/ha_shutdown.service $DEST
rsync --progress --checksum $HA/configuration.yaml $DEST
rsync --progress --checksum $HA/automations.yaml $DEST
