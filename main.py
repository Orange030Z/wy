import requests
import yaml
import base64
import os
import urllib3
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- [配置区] ---
UUID = os.getenv("MY_UUID", "5a2c16f9-e365-4080-8d38-6924c3835586")
HOST = os.getenv("MY_HOST", "snippets.kkii.eu.org")
MAX_WORKERS = 30 
SUFFIX = " @schpd_chat"

def check_ip_port(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
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
                if "#" not in line: continue
                addr, _ = line.split("#")
                if ":" not in addr: continue
                ip, port = addr.split(":")
                
                if check_ip_port(ip, port):
                    node_name = f"{name} {str(index + 1).zfill(2)}{SUFFIX}"
                    path = f"/{ip}:{port}"
                    # 构造 VLESS 链接
                    vless_link = f"vless://{UUID}@{ip}:{port}?encryption=none&security=tls&sni={HOST}&type=ws&host={HOST}&path={path}#{node_name}"
                    
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
                        "ws-opts": {"path": path, "headers": {"Host": HOST}},
                        "raw_url": vless_link # 确保这里一定有这个键
                    })
    except:
        pass
    return nodes_data

def main():
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
    print(f"正在全量抓取 {len(region_map)} 个地区...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_region, c, n) for c, n in region_map.items()]
        for future in as_completed(futures):
            all_proxies.extend(future.result())

    if not all_proxies:
        print("未抓取到有效节点")
        return

    all_proxies.sort(key=lambda x: x['name'])

    # 构造 Clash 配置
    clash_config = {
        "global-ua": "clash.meta",
        "mixed-port": 7890,
        "allow-lan": True,
        "mode": "rule",
        "log-level": "info",
        "ipv6": False,
        "dns": {
            "enable": True, "enhanced-mode": "fake-ip", "fake-ip-range": "198.18.0.1/16",
            "nameserver": ["https://doh.pub/dns-query", "https://223.5.5.5/dns-query"],
            "fallback": ["8.8.8.8", "1.1.1.1"]
        },
        "proxies": [{"name": "🟢 直连", "type": "direct", "udp": True}] + all_proxies,
        "proxy-groups": [
            {"name": "🚀 节点选择", "type": "select", "proxies": ["♻️ 自动选择", "☢ 负载均衡-散列", "🌐 全部节点", "🇭🇰 香港节点", "🇺🇲 美国节点", "🟢 直连"]},
            {"name": "♻️ 自动选择", "type": "url-test", "include-all": True, "url": "http://www.gstatic.com/generate_204", "interval": 300},
            {"name": "☢ 负载均衡-散列", "type": "load-balance", "strategy": "consistent-hashing", "include-all": True, "interval": 180},
            {"name": "🌐 全部节点", "type": "select", "include-all": True},
            {"name": "🇭🇰 香港节点", "type": "url-test", "include-all": True, "filter": "香港|HK"},
            {"name": "🇺🇲 美国节点", "type": "url-test", "include-all": True, "filter": "美国|US"}
        ],
        "rules": ["MATCH,🚀 节点选择"]
    }

    # 导出 Clash 配置
    with open("clash.yaml", "w", encoding="utf-8") as f:
        yaml.dump(clash_config, f, allow_unicode=True, sort_keys=False)
    
    # 安全导出 sub.txt 和 nodes.txt (增加 .get 保护)
    raw_urls = [n.get('raw_url') for n in all_proxies if n.get('raw_url')]
    if raw_urls:
        with open("nodes.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(raw_urls))
        with open("sub.txt", "w", encoding="utf-8") as f:
            f.write(base64.b64encode("\n".join(raw_urls).encode("utf-8")).decode("utf-8"))

    print(f"成功完成！共抓取 {len(all_proxies)} 个节点。")

if __name__ == "__main__":
    main()
