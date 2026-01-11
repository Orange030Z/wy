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
MAX_WORKERS = 30  # 增加并发，全量抓取时速度更快
SUFFIX = " @Orange"

def check_ip_port(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.8) # 稍微缩短超时，加快扫描速度
        result = s.connect_ex((ip, int(port)))
        s.close()
        return result == 0
    except:
        return False

def process_region(code, name):
    api_url = f"https://proxyip.881288.xyz/api/txt/{code}"
    headers = {'User-Agent': 'v2rayN/6.23'}
    nodes_data = []
    try:
        res = requests.get(api_url, headers=headers, verify=False, timeout=15)
        if res.status_code == 200:
            lines = [l.strip() for l in res.text.splitlines() if l.strip()]
            # --- 【这里已修改：去掉 [:10]，抓取该地区所有节点】 ---
            for index, line in enumerate(lines): 
                if "#" in line:
                    addr, _ = line.split("#")
                    ip, port = addr.split(":")
                    if check_ip_port(ip, port):
                        node_name = f"{name} {str(index + 1).zfill(2)}{SUFFIX}"
                        path = f"/{ip}:{port}"
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
                            "ws-opts": {"path": path, "headers": {"Host": HOST}}
                        })
    except: pass
    return nodes_data

def main():
    # 你的 50+ 完整地区列表
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
    print(f"正在全量抓取 {len(region_map)} 个地区的所有可用节点...")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_region, c, n): n for c, n in region_map.items()}
        for future in as_completed(futures):
            all_proxies.extend(future.result())

    if not all_proxies:
        print("未抓取到任何有效节点。")
        return

    all_proxies.sort(key=lambda x: x['name'])

    # --- [构建 suiyuan8 config3 风格配置] ---
    clash_config = {
        "global-ua": "clash.meta",
        "mixed-port": 7890,
        "allow-lan": True,
        "mode": "rule",
        "log-level": "info",
        "ipv6": False,
        "sniffer": {"enable": True, "sniff": {"HTTP": {"ports": [80, "8080-8880"], "override-destination": True}, "TLS": {"ports": [443, 8443]}, "QUIC": {"ports": [443, 8443]}}},
        "tun": {"enable": True, "stack": "mixed", "mtu": 9000, "auto-route": True, "auto-detect-interface": True},
        "dns": {
            "enable": True, "listen": "0.0.0.0:53", "enhanced-mode": "fake-ip", "fake-ip-range": "198.18.0.1/16",
            "nameserver": ["https://doh.pub/dns-query", "https://223.5.5.5/dns-query"],
            "fallback": ["https://1.1.1.1/dns-query", "8.8.8.8"]
        },
        # 注入所有抓取到的节点
        "proxies": [{"name": "🟢 直连", "type": "direct", "udp": True}] + all_proxies,
        
        "proxy-groups": [
            {"name": "🚀 节点选择", "type": "select", "proxies": ["♻️ 自动选择", "☢ 负载均衡-散列", "☢ 负载均衡-轮询", "🌐 全部节点", "🇭🇰 香港节点", "🇹🇼 台湾节点", "🇯🇵 日本节点", "🇸🇬 新加坡", "🇰🇷 韩国", "🇺🇲 美国节点", "🇩🇪 德国节点", "🇬🇧 英国节点", "🧿 其它地区", "🟢 直连"]},
            {"name": "♻️ 自动选择", "type": "url-test", "include-all": True, "tolerance": 20, "interval": 300, "filter": "^((?!(直连)).)*$"},
            {"name": "☢ 负载均衡-散列", "type": "load-balance", "strategy": "consistent-hashing", "include-all": True, "interval": 180},
            {"name": "☢ 负载均衡-轮询", "type": "load-balance", "strategy": "round-robin", "include-all": True, "interval": 180},
            {"name": "🌐 全部节点", "type": "select", "include-all": True},
            # 应用分流
            {"name": "📹 YouTube", "type": "select", "proxies": ["🚀 节点选择", "♻️ 自动选择", "🟢 直连"], "include-all": True},
            {"name": "🍀 Google", "type": "select", "proxies": ["🚀 节点选择", "♻️ 自动选择", "🟢 直连"], "include-all": True},
            {"name": "🤖 AI", "type": "select", "proxies": ["🚀 节点选择", "♻️ 自动选择", "🟢 直连"], "include-all": True},
            {"name": "📲 Telegram", "type": "select", "proxies": ["🚀 节点选择", "♻️ 自动选择", "🟢 直连"], "include-all": True},
            {"name": "🎯 全球直连", "type": "select", "proxies": ["🟢 直连", "🚀 节点选择"]},
            {"name": "🐟 漏网之鱼", "type": "select", "proxies": ["🚀 节点选择", "🟢 直连"]},
            # 地区分组过滤 (suiyuan8 风格的核心)
            {"name": "🇭🇰 香港节点", "type": "url-test", "include-all": True, "filter": "香港|HK"},
            {"name": "🇹🇼 台湾节点", "type": "url-test", "include-all": True, "filter": "台湾|TW"},
            {"name": "🇯🇵 日本节点", "type": "url-test", "include-all": True, "filter": "日本|JP"},
            {"name": "🇸🇬 新加坡", "type": "url-test", "include-all": True, "filter": "新加坡|SG"},
            {"name": "🇰🇷 韩国", "type": "url-test", "include-all": True, "filter": "韩国|KR"},
            {"name": "🇺🇲 美国节点", "type": "url-test", "include-all": True, "filter": "美国|US"},
            {"name": "🇬🇧 英国节点", "type": "url-test", "include-all": True, "filter": "英国|GB"},
            {"name": "🇩🇪 德国节点", "type": "url-test", "include-all": True, "filter": "德国|DE"},
            {"name": "🧿 其它地区", "type": "select", "include-all": True, "filter": "^((?!(香港|台湾|日本|新加坡|韩国|美国|英国|德国)).)*$"}
        ],
        "rule-providers": {
            "ai_ip": {"type": "http", "interval": 86400, "behavior": "ipcidr", "format": "mrs", "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/refs/heads/meta/geo/geoip/ai.mrs"},
            "youtube_domain": {"type": "http", "interval": 86400, "behavior": "domain", "format": "mrs", "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/youtube.mrs"},
            "google_domain": {"type": "http", "interval": 86400, "behavior": "domain", "format": "mrs", "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/google.mrs"},
            "telegram_ip": {"type": "http", "interval": 86400, "behavior": "ipcidr", "format": "mrs", "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geoip/telegram.mrs"},
            "cn_domain": {"type": "http", "interval": 86400, "behavior": "domain", "format": "mrs", "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/cn.mrs"}
        },
        "rules": [
            "RULE-SET,ai_ip,🤖 AI",
            "RULE-SET,youtube_domain,📹 YouTube",
            "RULE-SET,google_domain,🍀 Google",
            "RULE-SET,telegram_ip,📲 Telegram",
            "RULE-SET,cn_domain,🎯 全球直连",
            "MATCH,🐟 漏网之鱼"
        ]
    }

    # 4. 导出文件
    with open("clash.yaml", "w", encoding="utf-8") as f:
        yaml.dump(clash_config, f, allow_unicode=True, sort_keys=False)
    
    # 导出 sub.txt 和 nodes.txt
    raw_urls = [n['raw_url'] for n in all_proxies]
    with open("nodes.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(raw_urls))
    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(base64.b64encode("\n".join(raw_urls).encode("utf-8")).decode("utf-8"))

    print(f"完成！共抓取并验证了 {len(all_proxies)} 个可用节点。")

if __name__ == "__main__":
    main()
