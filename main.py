import requests
import yaml
import base64
import os
import urllib3
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- [配置区] ---
UUID = os.getenv("MY_UUID", "3afad5df-e056-4301-846d-665b4ef51968")
HOST = os.getenv("MY_HOST", "x.kkii.eu.org")
MAX_WORKERS = 30 
SUFFIX = " @Orange"

def check_ip_port(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.6) # 缩短检测时间，防止 Actions 超时
        result = s.connect_ex((ip, int(port)))
        s.close()
        return result == 0
    except:
        return False

def process_region(code, name):
    api_url = f"https://proxyip.881288.xyz/api/txt/{code}"
    nodes_data = []
    try:
        res = requests.get(api_url, timeout=10, verify=False)
        if res.status_code == 200:
            lines = [l.strip() for l in res.text.splitlines() if "#" in l]
            for index, line in enumerate(lines):
                addr, _ = line.split("#")
                ip, port = addr.split(":")
                if check_ip_port(ip, port):
                    node_name = f"{name} {str(index + 1).zfill(2)}{SUFFIX}"
                    nodes_data.append({
                        "name": node_name,
                        "type": "vless",
                        "server": ip,
                        "port": int(port),
                        "uuid": UUID,
                        "cipher": "auto",
                        "tls": True,
                        "udp": True,
                        "servername": HOST,
                        "network": "ws",
                        "ws-opts": {"path": f"/{ip}:{port}", "headers": {"Host": HOST}}
                    })
    except:
        pass
    return nodes_data

def main():
    # 完整 50+ 地区
    region_map = {
        "HK": "香港", "TW": "台湾", "JP": "日本", "KR": "韩国", "SG": "新加坡",
        "MY": "马来西亚", "TH": "泰国", "VN": "越南", "ID": "印尼", "PH": "菲律宾",
        "MM": "缅甸", "LA": "老挝", "KH": "柬埔寨", "BD": "孟加拉", "IN": "印度",
        "PK": "巴基斯坦", "BN": "文莱", "US": "美国", "CA": "加拿大", "MX": "墨西哥",
        "BR": "巴西", "AR": "阿根廷", "CL": "智利", "CO": "哥伦比亚", "PE": "秘鲁",
        "GB": "英国", "DE": "德国", "FR": "法国", "NL": "荷兰", "RU": "俄罗斯",
        "IT": "意大利", "ES": "西班牙", "TR": "土耳其", "PL": "波兰", "UA": "乌克兰",
        "SE": "瑞典", "FI": "芬兰", "NO": "挪威", "DK": "丹麦", "CZ": "捷克",
        "RO": "罗马尼亚", "CH": "瑞士", "PT": "葡萄牙", "AU": "澳大利亚", "NZ": "新西兰",
        "ZA": "南非", "EG": "埃及", "NG": "尼日利亚", "SA": "沙特", "AE": "阿联酋",
        "IL": "以色列", "IR": "伊朗", "IQ": "伊拉克"
    }

    all_proxies = []
    print(f"正在全量检测 {len(region_map)} 个地区的节点...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_region, c, n) for c, n in region_map.items()]
        for future in as_completed(futures):
            all_proxies.extend(future.result())

    if not all_proxies:
        print("抓取失败")
        return

    # --- [suiyuan8 config3 结构注入] ---
    config = {
        "global-ua": "clash.meta",
        "mixed-port": 7890,
        "allow-lan": True,
        "mode": "rule",
        "log-level": "info",
        "ipv6": False,
        "sniffer": {"enable": True, "sniff": {"HTTP": {"ports": [80, "8080-8880"], "override-destination": True}, "TLS": {"ports": [443, 8443]}, "QUIC": {"ports": [443, 8443]}}},
        "tun": {"enable": True, "stack": "mixed", "auto-route": True, "auto-detect-interface": True},
        "dns": {
            "enable": True, "listen": "0.0.0.0:53", "enhanced-mode": "fake-ip", "fake-ip-range": "198.18.0.1/16",
            "nameserver": ["https://doh.pub/dns-query", "https://223.5.5.5/dns-query"],
            "fallback": ["8.8.8.8", "1.1.1.1"]
        },
        "proxies": [{"name": "🟢 直连", "type": "direct"}] + all_proxies,
        "proxy-groups": [
            {"name": "🚀 节点选择", "type": "select", "proxies": ["♻️ 自动选择", "☢ 负载均衡-散列", "🌐 全部节点", "🇭🇰 香港节点", "🇹🇼 台湾节点", "🇯🇵 日本节点", "🇸🇬 新加坡", "🇰🇷 韩国", "🇺🇲 美国节点", "🟢 直连"]},
            {"name": "♻️ 自动选择", "type": "url-test", "include-all": True, "url": "http://www.gstatic.com/generate_204", "interval": 300},
            {"name": "☢ 负载均衡-散列", "type": "load-balance", "include-all": True, "strategy": "consistent-hashing", "url": "http://www.gstatic.com/generate_204", "interval": 180},
            {"name": "🌐 全部节点", "type": "select", "include-all": True},
            # 地区分组过滤
            {"name": "🇭🇰 香港节点", "type": "url-test", "include-all": True, "filter": "香港|HK"},
            {"name": "🇹🇼 台湾节点", "type": "url-test", "include-all": True, "filter": "台湾|TW"},
            {"name": "🇯🇵 日本节点", "type": "url-test", "include-all": True, "filter": "日本|JP"},
            {"name": "🇸🇬 新加坡", "type": "url-test", "include-all": True, "filter": "新加坡|SG"},
            {"name": "🇰🇷 韩国", "type": "url-test", "include-all": True, "filter": "韩国|KR"},
            {"name": "🇺🇲 美国节点", "type": "url-test", "include-all": True, "filter": "美国|US"},
            {"name": "🧿 其它地区", "type": "select", "include-all": True, "filter": "^((?!(香港|台湾|日本|新加坡|韩国|美国)).)*$"}
        ],
        "rule-providers": {
            "ai_ip": {"type": "http", "interval": 86400, "behavior": "ipcidr", "format": "mrs", "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/refs/heads/meta/geo/geoip/ai.mrs"},
            "cn_domain": {"type": "http", "interval": 86400, "behavior": "domain", "format": "mrs", "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/cn.mrs"}
        },
        "rules": [
            "RULE-SET,ai_ip,🚀 节点选择",
            "RULE-SET,cn_domain,DIRECT",
            "MATCH,🚀 节点选择"
        ]
    }

    with open("clash.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f
