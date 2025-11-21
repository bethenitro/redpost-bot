import requests
import logging

# Note: For SOCKS proxy support, ensure PySocks is installed:
# pip install pysocks

# ----------------------------
# Logging setup
# ----------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ----------------------------
# Proxy configuration
# ----------------------------
# Example configurations for different proxy types:

# HTTP proxy (replace with your actual proxy)
# proxy = "http://username:password@proxy.example.com:8080"

# SOCKS5 proxy (replace with your actual proxy)
proxy = "socks5://username:password@proxy.example.com:1080"

# SOCKS4 proxy (replace with your actual proxy)
# proxy = "socks4://username:password@proxy.example.com:1080"

# No authentication example
# proxy = "socks5://proxy.example.com:1080"

# For HTTP/HTTPS proxies
if proxy.startswith(("http://", "https://")):
    proxies = {
        "http": proxy,
        "https": proxy
    }
# For SOCKS proxies, requests will handle them automatically with PySocks
else:
    proxies = {
        "http": proxy,
        "https": proxy
    }

logging.debug(f"Using proxy configuration: {proxies}")


# ----------------------------
# Helper functions
# ----------------------------
def get_public_ip():
    services = [
        "https://api.ipify.org?format=json",
        "https://ifconfig.me/ip",
        "https://ipinfo.io/ip",
        "https://ident.me"
    ]

    for url in services:
        logging.debug(f"Trying IP service: {url}")

        try:
            r = requests.get(url, proxies=proxies, timeout=10)
            logging.debug(f"Status code from {url}: {r.status_code}")
            logging.debug(f"Response text: {r.text[:200]}")  # print first 200 chars

            t = r.text.strip()

            # ipify returns JSON
            if t.startswith("{"):
                ip = r.json().get("ip")
                logging.info(f"Received IP from {url}: {ip}")
                return ip

            logging.info(f"Received IP from {url}: {t}")
            return t

        except Exception as e:
            logging.error(f"Error contacting {url}: {e}")

    logging.error("All services failed.")
    return None


def get_geolocation(ip):
    url = f"https://ipwho.is/{ip}"
    logging.debug(f"Querying geolocation: {url}")
    try:
        r = requests.get(url, proxies=proxies, timeout=10)
        logging.debug(f"Geo status: {r.status_code}")
        logging.debug(f"Geo response: {r.text[:300]}")
        return r.json()
    except Exception as e:
        logging.error(f"Geo lookup failed: {e}")
        return {}


# ----------------------------
# Main execution
# ----------------------------
ip = get_public_ip()
logging.info(f"Public IP resolved: {ip}")

if ip:
    geo = get_geolocation(ip)
    logging.info(f"City = {geo.get('city')}")
    print("City:", geo.get("city"))
else:
    print("Failed to get public IP.")
