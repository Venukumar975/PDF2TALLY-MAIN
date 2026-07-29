import requests

def debug():
    url = 'http://127.0.0.1:51974/api/tally/vouchers'
    payload = {
        'company_name': 'Tally Test',
        'bank_name': 'BOB',
        'from_date': '2025-04-02',
        'to_date': '2025-04-30'
    }
    
    r = requests.post(url, json=payload)
    vouchers = r.json().get('vouchers', [])
    print(f"Total April Vouchers: {len(vouchers)}")
    
    for idx, v in enumerate(vouchers):
        print(f"#{idx+1}: Date: {v['date']}, No: {v['vch_no']}, Type: {v['vch_type']}, Amt: {v['amount']}, Type: {v['type']}, Part: {v['particulars']}, Narr: {v['narration']}")

if __name__ == "__main__":
    debug()
