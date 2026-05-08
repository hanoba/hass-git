sudo docker run -d \
  --name homeassistant \
  --privileged \
  --restart=unless-stopped \
  -e TZ=Europe/Berlin \
  -v /home/$(whoami)/homeassistant:/config \
  --network=host \
  --device /dev/gpiomem \
  ghcr.io/home-assistant/raspberrypi2-homeassistant:stable

