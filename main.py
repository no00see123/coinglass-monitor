import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import os

URL = 'https://www.coinglass.com/zh'
DATA_FILE = 'data.json'  # 持久化文件

def parse_value(value_str):
    """解析数值，如'615.80亿' -> 61580000000 (美元)"""
    if '亿' in value_str:
        return float(value_str.replace('亿', '').replace('$', '').strip()) * 100000000
    elif '%' in value_str:
        return float(value_str.replace('%', '').replace('+', '').strip())
    return float(value_str.replace('$', '').strip()) if value_str else 0.0

def scrape_data():
    response = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table')  # 假设第一个table为目标
    if not table:
        return []  # 异常处理
    rows = table.find_all('tr')
    data = []
    for row in rows[1:]:  # 跳过header
        cells = row.find_all('td')
        if len(cells) < 12: continue
        symbol = cells[2].text.strip()  # 币种
        oi = parse_value(cells[9].text.strip())  # 持仓 (美元)
        oi_1h_change = parse_value(cells[10].text.strip())  # 持仓(1h%)
        oi_24h_change = parse_value(cells[11].text.strip())  # 持仓(24h%)
        volume_24h = parse_value(cells[6].text.strip())  # 24h成交额 (假设单位亿美元)
        volume_24h_change = parse_value(cells[7].text.strip())  # 成交额(24h%)
        data.append({
            'symbol': symbol,
            'oi': oi,
            'oi_1h_change': oi_1h_change,
            'oi_24h_change': oi_24h_change,
            'volume_24h': volume_24h,
            'volume_24h_change': volume_24h_change
        })
    return data

def load_history():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}  # {symbol: {'records': [{'time': , 'oi': , 'oi_1h_change': , 'volume_24h_change': }], 'start_time': , 'duration': }}

def save_history(history):
    with open(DATA_FILE, 'w') as f:
        json.dump(history, f, ensure_ascii=False)

def monitor():
    raw_data = scrape_data()
    # 筛选: oi > 10000000, volume_24h > 20000000
    filtered = [d for d in raw_data if d['oi'] > 10000000 and d['volume_24h'] > 20000000]
    # 排序: oi_1h_change 降序
    filtered.sort(key=lambda x: x['oi_1h_change'], reverse=True)
    
    history = load_history()
    now = datetime.now().isoformat()
    
    for item in filtered[:20]:  # 限制前20，避免过多
        symbol = item['symbol']
        change = item['oi_1h_change']
        if symbol not in history:
            history[symbol] = {'records': [], 'start_time': None, 'duration': None}
        
        rec = {'time': now, 'oi': item['oi'], 'oi_1h_change': change, 'volume_24h_change': item['volume_24h_change']}
        history[symbol]['records'].append(rec)
        
        if change > 5:
            if not history[symbol]['start_time']:
                history[symbol]['start_time'] = now
        else:
            if history[symbol]['start_time']:
                start = datetime.fromisoformat(history[symbol]['start_time'])
                duration = (datetime.fromisoformat(now) - start).total_seconds() / 60  # 分钟
                history[symbol]['duration'] = duration
                history[symbol]['start_time'] = None  # 重置
    
    save_history(history)
    # 清理已完成监控的币种（可选，保留历史）
    return history

if __name__ == '__main__':
    monitor()
