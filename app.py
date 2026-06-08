from flask import Flask, request, jsonify
from datetime import datetime
from collections import defaultdict
import os

app = Flask(__name__)

TOKEN = "kairos_79942de021a74dc095580363fc380b64"
SYMBOLS = ['XAUUSD', 'NAS100']

alerts_queue = defaultdict(list)
stats = {'XAUUSD': {'received': 0, 'sent': 0}, 'NAS100': {'received': 0, 'sent': 0}}

def validate_token(token):
    return token == TOKEN

def get_time():
    return datetime.utcnow().isoformat() + 'Z'

@app.route('/api/tv', methods=['POST'])
def receive_alert():
    token = request.args.get('token')

    if not validate_token(token):
        return jsonify({'error': 'Invalid token', 'ok': False}), 401

    try:
        data = request.get_json()
        symbol = data.get('broker_symbol')
        side = data.get('side')
        price = data.get('price')

        if not all([symbol, side, price]):
            return jsonify({'error': 'Missing fields', 'ok': False}), 400

        if symbol not in SYMBOLS:
            return jsonify({'error': f'Unknown symbol', 'ok': False}), 400

        alerts_queue[symbol].append(data)
        stats[symbol]['received'] += 1

        print(f"[{get_time()}] Alert received: {symbol} {side} @ {price}")

        return jsonify({'ok': True, 'queued': len(alerts_queue[symbol])}), 200

    except Exception as e:
        return jsonify({'error': str(e), 'ok': False}), 500


@app.route('/api/mt5/next', methods=['GET', 'POST'])
def get_next_alert():
    token = request.args.get('token') or (request.get_json() or {}).get('token')
    symbol = request.args.get('symbol') or (request.get_json() or {}).get('symbol')

    if not validate_token(token):
        return jsonify({'error': 'Invalid token', 'ok': False}), 401

    if not symbol or symbol not in SYMBOLS:
        return jsonify({'error': 'Invalid symbol', 'ok': False}), 400

    if alerts_queue[symbol]:
        alert = alerts_queue[symbol].pop(0)
        stats[symbol]['sent'] += 1
        print(f"[{get_time()}] Alert sent to MT5: {symbol}")
        return alert, 200
    else:
        return {}, 200


@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        'ok': True,
        'server': 'running',
        'symbols': SYMBOLS,
        'stats': stats,
        'queues': {s: len(alerts_queue[s]) for s in SYMBOLS}
    }), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'status': 'healthy'}), 200


@app.route('/', methods=['GET'])
def root():
    return jsonify({'ok': True, 'server': 'Kairos TV Alerts Server', 'version': '1.0.0'}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
