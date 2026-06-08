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
    """Reçoit les alertes de TradingView"""
    token = request.args.get('token')

    if not validate_token(token):
        return jsonify({'error': 'Invalid token', 'ok': False}), 401

    try:
        data = request.get_json()
        
        # Mapper les champs de l'indicateur Pine Script
        symbol = data.get('broker_symbol')  # ← "broker_symbol" au lieu de "symbol"
        direction = data.get('side')        # ← "side" au lieu de "direction"
        price = data.get('price')
        time_val = data.get('bar_time', get_time())

        if not all([symbol, direction, price]):
            return jsonify({'error': 'Missing: broker_symbol, side, price', 'ok': False}), 400

        if symbol not in SYMBOLS:
            return jsonify({'error': f'Unknown symbol. Use: {", ".join(SYMBOLS)}', 'ok': False}), 400

        alert = {
            'symbol': symbol,
            'direction': direction,
            'price': price,
            'time': time_val,
            'receivedAt': get_time(),
            'full_data': data  # Garder toutes les données
        }

        alerts_queue[symbol].append(alert)
        stats[symbol]['received'] += 1

        print(f"[{get_time()}] Alert received: {symbol} {direction} @ {price}")

        return jsonify({
            'ok': True,
            'message': f'Alert received for {symbol}',
            'symbol': symbol,
            'queued': len(alerts_queue[symbol])
        }), 200

    except Exception as e:
        return jsonify({'error': str(e), 'ok': False}), 500


@app.route('/api/mt5/next', methods=['GET', 'POST'])
def get_next_alert():
    """Sert l'alerte suivante à MT5"""
    token = request.args.get('token') or (request.get_json() or {}).get('token')
    symbol = request.args.get('symbol') or (request.get_json() or {}).get('symbol')

    if not validate_token(token):
        return jsonify({'error': 'Invalid token', 'ok': False}), 401

    if not symbol or symbol not in SYMBOLS:
        return jsonify({'error': f'Invalid symbol. Use: {", ".join(SYMBOLS)}', 'ok': False}), 400

    if alerts_queue[symbol]:
        alert = alerts_queue[symbol].pop(0)
        stats[symbol]['sent'] += 1
        print(f"[{get_time()}] Alert sent to MT5: {symbol}")
        return jsonify({
            'ok': True,
            'alert': alert,
            'symbol': symbol,
            'queued': len(alerts_queue[symbol])
        }), 200
    else:
        return jsonify({
            'ok': True,
            'alert': None,
            'symbol': symbol,
            return jsonify(alert), 200
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
    return jsonify({
        'ok': True,
        'server': 'Kairos TV Alerts Server',
        'version': '1.0.0'
    }), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
