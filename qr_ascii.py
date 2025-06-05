import qrcode
from textual.app import App, ComposeResult
from textual.widgets import Label
from textual import containers



def qr_ascii(data: str) -> str:
    qr = qrcode.QRCode(border=2)
    qr.add_data(data)
    qr.make(fit=True)
    # Captura el QR como texto ASCII
    import io
    buf = io.StringIO()
    qr.print_ascii(out=buf, invert=True)
    return buf.getvalue()

class Run_qr(App):
    CSS_PATH = "styles.css"
    def on_mount(self) -> None:
        lines_conf = []
        lines_conf.append("[Interface]")       
        lines_conf.append("PrivateKey = GOxvcAcYRuW8OZ8496RB6TDPNl90xWrHzgky8w0eJls=")
        lines_conf.append("Address = 10.8.0.2/32")
        lines_conf.append("DNS = 1.1.1.1")
        lines_conf.append("")
        lines_conf.append("[Peer]")
        lines_conf.append("PublicKey    = yNMWN4IuBZrTva6JO5hqgMFIONCcIO+2C2v2mtIJPwQ=")
        lines_conf.append("PresharedKey = 0xYbLyG0Zo10ZoaVv1KkLRpF/vsB4fpLXNIRYz8DKmE=")
        lines_conf.append("AllowedIPs   = 0.0.0.0/0, ::/0")
        lines_conf.append("PersistentKeepalive = 0")
        lines_conf.append("Endpoint = 192.168.1.134:51820")
        qr_text = qr_ascii(
            "\n".join(lines_conf)
        )
        self.query_one("#qr", Label).update(qr_text)

    def compose(self) -> ComposeResult:
        with containers.Container(classes="qr_container"):
            yield Label("QR Code")
            yield Label(id="qr")

if __name__ == "__main__":
    app = Run_qr()
    app.run()