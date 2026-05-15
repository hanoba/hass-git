from http.server import BaseHTTPRequestHandler, HTTPServer
import os

class ShutdownHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Einfache Sicherheitsprüfung: URL muss /shutdown_host sein
        if self.path == '/shutdown_host':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Shutdown initiated")
            print("Shutdown-Befehl von HA empfangen...")
            #os.system("sudo shutdown -h now")
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    # Port 8080 (oder ein anderer freier Port)
    server = HTTPServer(('0.0.0.0', 8080), ShutdownHandler)
    print("Listener läuft auf Port 8080...")
    server.serve_forever()
