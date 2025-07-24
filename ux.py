from flask import Flask, render_template_string, request, jsonify
import requests
import urllib3
from datetime import datetime
import traceback
import asyncio
from hyperliquid.utils import constants
import example_utils_3  # Changed back to example_utils
from typing import Optional, Dict, List, Tuple

app = Flask(__name__)

# Default addresses
LEDGER_ADDRESS = "0x87d1910BE2AaE6D9C22F15AC9009Ec8Ca8706BAd"
TRADE_WALLET = "0x2a21Cc5D8Bcaa0D10078C99606B03Ee46C58817d"
DEX_WALLET = "0x62E485fD0e5c7D32f8cCF11aa356A1179C76e400"

# Error handling configuration
MAX_RETRIES = 5
RETRY_DELAY = 10  # seconds between retries

def make_api_request(request_type, user_address):
    """Make API request to Hyperliquid"""
    url = "https://api.hyperliquid.xyz/info"
    request_body = {
        "type": request_type,
        "user": user_address
    }
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=request_body, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, f"Error {response.status_code}: {response.text}"
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {str(e)}"

async def make_an_order(coin, buy_or_sell, size, price, retries=MAX_RETRIES):
    """Place a buy or sell order"""
    print(f"DEBUG: Attempting to place order - Coin: {coin}, Buy: {buy_or_sell}, Size: {size}, Price: {price}")
    address, info, exchange = example_utils_3.setup(base_url=constants.MAINNET_API_URL, skip_ws=True)
    
    for attempt in range(retries):
        try:
            if buy_or_sell:
                # Place a BUY order
                order_result = exchange.order(coin, True, size, price, {"limit": {"tif": "Gtc"}})
                print(f"Buy order: {order_result}")
            else:
                # Place a SELL order
                order_result = exchange.order(coin, False, size, price, {"limit": {"tif": "Gtc"}})
                print(f"Sell order: {order_result}")
            return order_result
        except (requests.exceptions.RequestException, urllib3.exceptions.ProtocolError) as e:
            print(f"Error placing order: {e}")
            print(f"Retrying in {RETRY_DELAY} seconds...")
            await asyncio.sleep(RETRY_DELAY)
    
    print("Failed to place order after multiple retries.")
    return None

def run_async_make_order(coin, buy_or_sell, size, price):
    """Wrapper to run async make_order function"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(make_an_order(coin, buy_or_sell, size, price))
        loop.close()
        return result
    except Exception as e:
        print(f"Error running make_order function: {str(e)}")
        return None

def get_spot_asset_balances(account_address, asset_name=None):
    """Gets the balance of the supplied asset for the supplied address"""
    url = "https://api.hyperliquid.xyz/info"
    headers = {
        "Content-Type": "application/json"
    }
    body = {
        "type": "spotClearinghouseState",
        "user": account_address
    }
    
    try:
        response = requests.post(url, headers=headers, json=body, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "balances" in data:
                if asset_name:
                    # Filter out the balance of the specified asset
                    asset_balance = next((balance for balance in data["balances"] if balance["coin"] == asset_name), None)
                    return asset_balance
                else:
                    return data["balances"]
            else:
                return None
        else:
            return None
    except Exception as e:
        print(f"Error fetching spot balances: {str(e)}")
        return None

def get_all_asset_data() -> Optional[Tuple[Dict[str, str], Dict[str, float]]]:
    """
    Fetches all asset data and returns both symbol-to-ID mapping and prices.
    
    Returns:
        Tuple of (symbol_to_id_dict, price_dict) or None if error
    """
    url = "https://api.hyperliquid.xyz/info"
    headers = {
        "Content-Type": "application/json"
    }
    body = {
        "type": "spotMetaAndAssetCtxs"
    }
    
    try:
        response = requests.post(url, headers=headers, json=body, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, list) and len(data) >= 2:
            universe = data[0]  # Universe data with symbol mappings
            assets = data[1]    # Asset price data
            
            # Build price dictionary first
            price_dict = {}
            for asset in assets:
                coin_id = asset.get('coin')  # This is like '@107', '@1', etc.
                midPx = asset.get('midPx')
                if coin_id and midPx is not None:
                    price_dict[coin_id] = float(midPx)
            
            # Create a mapping from token names to their actual price IDs
            symbol_to_id = {}
            
            # Handle tokens
            if 'tokens' in universe:
                token_index_to_name = {}
                for token in universe['tokens']:
                    token_name = token['name']
                    token_index = token['index']
                    token_index_to_name[token_index] = token_name
                
                # Now map universe trading pairs to token names
                if 'universe' in universe:
                    for market in universe['universe']:
                        market_name = market['name']  # e.g., '@1', '@2', etc.
                        tokens = market.get('tokens', [])
                        
                        # If this market has tokens, map the first token to this market ID
                        if len(tokens) >= 2:
                            # tokens[0] is usually USDC (index 0), tokens[1] is the actual token
                            token_index = tokens[0] if tokens[0] != 0 else tokens[1]
                            if token_index in token_index_to_name:
                                token_symbol = token_index_to_name[token_index]
                                symbol_to_id[token_symbol] = market_name
            
            # Special handling for known tokens
            known_mappings = {
                'HYPE': '@107',
                'PURR': '@1',
                'FUSD': '@153',
                'USDT0': '@166',
                'USDHL': '@180',
                # Add more as needed
            }
            
            for symbol, price_id in known_mappings.items():
                if price_id in price_dict:
                    symbol_to_id[symbol] = price_id
            
            # Handle USDC specially
            symbol_to_id['USDC'] = 'USDC'
            price_dict['USDC'] = 1.0
            
            return symbol_to_id, price_dict
        
        return None
        
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error fetching asset data: {e}")
        return None

def calculate_portfolio_value(account_address: str) -> Tuple[List[Dict], float]:
    """
    Calculate the total portfolio value in USDC for all non-zero balances.
    
    Returns:
        Tuple of (portfolio_details, total_value_usdc)
    """
    # Get all balances for the account
    balances = get_spot_asset_balances(account_address)
    if not balances:
        print("No balances found or error fetching balances")
        return [], 0.0
    
    # Get asset data (mappings and prices)
    asset_data = get_all_asset_data()
    if not asset_data:
        print("Error fetching asset data")
        return [], 0.0
    
    symbol_to_id, prices = asset_data
    
    portfolio = []
    total_value_usdc = 0.0
    
    for balance in balances:
        coin = balance.get('coin', '')
        total_balance = balance.get('total', '0')
        hold_balance = balance.get('hold', '0')
        
        # Use total balance for calculations
        try:
            balance_amount = float(total_balance)
            hold_amount = float(hold_balance) if hold_balance else 0.0
            
            # Skip if zero or negative balance
            if balance_amount <= 0:
                continue
        except (ValueError, TypeError):
            continue
        
        # Get the asset ID for this coin
        asset_id = symbol_to_id.get(coin, coin)  # Fallback to coin name if no mapping found
        
        # Get price for this asset
        if coin == 'USDC' or coin == 'USDC/USD':
            # USDC is the base currency, so price is 1
            price_usdc = 1.0
        else:
            # Try to get price using the asset ID
            price_usdc = prices.get(asset_id, 0.0)
            # If not found, try the original coin name
            if price_usdc == 0.0:
                price_usdc = prices.get(coin, 0.0)
        
        # Calculate USDC value using total balance
        usdc_value = balance_amount * price_usdc
        
        # Add to portfolio
        asset_info = {
            'coin': coin,
            'asset_id': asset_id,
            'total_balance': balance_amount,
            'hold_balance': hold_amount,
            'price_usdc': price_usdc,
            'value_usdc': usdc_value
        }
        portfolio.append(asset_info)
        total_value_usdc += usdc_value
    
    return portfolio, total_value_usdc

def format_spot_balances_with_values(balances, account_address):
    """Format spot balances for display with USDC values"""
    if not balances:
        return "<pre>No spot balances found.\n</pre>"
    
    # Calculate portfolio values
    portfolio, total_value = calculate_portfolio_value(account_address)
    
    # Create a lookup dict for values by coin
    value_lookup = {item['coin']: item for item in portfolio}
    
    result_text = "<pre>💰 Spot Balances with USDC Values:\n"
    result_text += "=" * 60 + "\n\n"
    
    # Sort balances by USDC value (descending)
    sorted_balances = []
    for balance in balances:
        coin = balance.get('coin', 'N/A')
        total = balance.get('total', '0')
        hold = balance.get('hold', '0')
        
        # Get value info
        value_info = value_lookup.get(coin, {})
        asset_id = value_info.get('asset_id', 'N/A')
        price_usdc = value_info.get('price_usdc', 0.0)
        value_usdc = value_info.get('value_usdc', 0.0)
        
        sorted_balances.append({
            'coin': coin,
            'asset_id': asset_id,
            'total': total,
            'hold': hold,
            'price_usdc': price_usdc,
            'value_usdc': value_usdc
        })
    
    # Sort by USDC value descending
    sorted_balances.sort(key=lambda x: x['value_usdc'], reverse=True)
    
    for balance in sorted_balances:
        coin = balance['coin']
        asset_id = balance['asset_id']
        total = balance['total']
        hold = balance['hold']
        price_usdc = balance['price_usdc']
        value_usdc = balance['value_usdc']
        
        # Convert to float and format with commas
        try:
            total_float = float(total)
            hold_float = float(hold)
            
            # Format numbers with commas and appropriate decimal places
            if total_float >= 1:
                total_formatted = f"{total_float:,.2f}".rstrip('0').rstrip('.')
            else:
                total_formatted = f"{total_float:.6f}".rstrip('0').rstrip('.')
            
            # Format price and value
            if price_usdc > 0:
                price_formatted = f"${price_usdc:.6f}".rstrip('0').rstrip('.')
                if price_formatted.endswith('$'):
                    price_formatted = "$0"
                value_formatted = f"${value_usdc:,.2f}"
            else:
                price_formatted = "$0"
                value_formatted = "$0.00"
            
            # Create the line with asset ID
            line = f"{coin} ({asset_id}) bal {total_formatted}"
            
            if hold_float > 0:
                if hold_float >= 1:
                    hold_formatted = f"{hold_float:,.2f}".rstrip('0').rstrip('.')
                else:
                    hold_formatted = f"{hold_float:.6f}".rstrip('0').rstrip('.')
                line += f" (hold: {hold_formatted})"
            
            # Add price and value info
            if price_usdc > 0:
                line += f" @ {price_formatted} = {value_formatted}"
            else:
                line += f" @ {price_formatted} = {value_formatted} (no price data)"
            
            result_text += line + "\n"
        
        except (ValueError, TypeError):
            result_text += f"{coin} ({asset_id}) bal {total}\n"
    
    # Add total portfolio value
    result_text += "\n" + "=" * 60 + "\n"
    result_text += f"💎 TOTAL PORTFOLIO VALUE: ${total_value:,.2f} USDC\n"
    result_text += "=" * 60 + "\n"
    result_text += "\n</pre>"
    return result_text

def format_spot_balances(balances):
    """Format spot balances for display (original function kept for compatibility)"""
    if not balances:
        return "<pre>No spot balances found.\n</pre>"
    
    result_text = "<pre>💰 Spot Balances:\n"
    result_text += "=" * 50 + "\n\n"
    
    # Sort balances by total value (descending)
    sorted_balances = sorted(balances, key=lambda x: float(x.get('total', '0')), reverse=True)
    
    for balance in sorted_balances:
        coin = balance.get('coin', 'N/A')
        total = balance.get('total', '0')
        hold = balance.get('hold', '0')
        
        # Convert to float and format with commas
        try:
            total_float = float(total)
            hold_float = float(hold)
            
            # Format numbers with commas and appropriate decimal places
            if total_float >= 1:
                total_formatted = f"{total_float:,.2f}".rstrip('0').rstrip('.')
            else:
                total_formatted = f"{total_float:.6f}".rstrip('0').rstrip('.')
            
            if hold_float > 0:
                if hold_float >= 1:
                    hold_formatted = f"{hold_float:,.2f}".rstrip('0').rstrip('.')
                else:
                    hold_formatted = f"{hold_float:.6f}".rstrip('0').rstrip('.')
                result_text += f"{coin} bal ${total_formatted} (hold: ${hold_formatted})\n"
            else:
                result_text += f"{coin} bal ${total_formatted}\n"
        
        except (ValueError, TypeError):
            result_text += f"{coin} bal ${total}\n"
    
    result_text += "\n</pre>"
    return result_text
                
def get_open_orders(user_address):
    """Get open orders for a user"""
    orders, error = make_api_request("openOrders", user_address)
    
    if error:
        return None, False, error
        
    if orders:
        return orders, True, None
    else:
        return None, False, "No open orders found"

def get_coin(symbol):
    """Convert symbol to coin name"""
    symbol_to_coin = {
        "@153": "FUSD",
        "@166": "USDT0", 
        "@180": "USDHL",
        "@107": "HYPE"
    }
    return symbol_to_coin.get(symbol, symbol)  # Return original symbol if not found

def get_coin_symbol(coin_name):
    """Convert coin name to symbol"""
    coin_to_symbol = {
        "FUSD": "@153",
        "USDT0": "@166", 
        "USDHL": "@180",
        "HYPE": "@107"
    }
    return coin_to_symbol.get(coin_name, coin_name)

async def cancel_order(coin, oid):
    print(f"DEBUG: Attempting to cancel order - Coin: {coin}, OID: {oid}")
    address, info, exchange = example_utils_3.setup(base_url=constants.MAINNET_API_URL, skip_ws=True)
    
    try:
        # Convert oid to integer as it might be expected as a number, not string
        oid_int = int(oid)
        print(f"DEBUG: Calling exchange.cancel with coin='{coin}', oid={oid_int} (converted to int)")
        cancel_result = exchange.cancel(coin, oid_int)
        print(f"DEBUG: Cancel result: {cancel_result}")
        return True, f"Order cancelled successfully: {cancel_result}"
        
    except ValueError as ve:
        error_msg = f"Invalid order ID format: {oid} - {str(ve)}"
        print(f"DEBUG: OID conversion failed: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Failed to cancel order: {str(e)}"
        print(f"DEBUG: Cancel failed with error: {error_msg}")
        return False, error_msg

def run_async_cancel(coin, oid):
    """Wrapper to run async cancel function"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success, result = loop.run_until_complete(cancel_order(coin, oid))
        loop.close()
        return success, result
    except Exception as e:
        return False, f"Error running cancel function: {str(e)}"

@app.route('/')
def index():
    """Main page"""
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hyperliquid Trading Interface</title>
    <link rel="stylesheet" href="/static/style.css">
    <style>
        /* Additional styles for the order form */
        .order-form {
            background: linear-gradient(135deg, #e6f3ff, #f0f8ff);
            border: 2px solid #4a90e2;
            border-radius: 15px;
            padding: 20px;
            margin: 15px 0;
        }
        
        .order-form h3 {
            color: #2c5282;
            margin-bottom: 15px;
            text-align: center;
        }
        
        .form-row {
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .form-row .form-group {
            flex: 1;
            margin-bottom: 0;
        }
        
        .order-type-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .order-type-group label {
            flex: 1;
            text-align: center;
            padding: 10px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            background: white;
        }
        
        .order-type-group input[type="radio"] {
            display: none;
        }
        
        .order-type-group input[type="radio"]:checked + span {
            background: #4a90e2;
            color: white;
            font-weight: bold;
        }
        
        .buy-order {
            border-color: #48bb78 !important;
        }
        
        .buy-order input[type="radio"]:checked + span {
            background: #48bb78 !important;
        }
        
        .sell-order {
            border-color: #f56565 !important;
        }
        
        .sell-order input[type="radio"]:checked + span {
            background: #f56565 !important;
        }
        
        .btn.place-order {
            background: linear-gradient(135deg, #4a90e2, #357abd);
            font-size: 1.1rem;
            padding: 16px 25px;
            margin-top: 10px;
        }
        
        .btn.place-order:hover {
            box-shadow: 0 10px 20px rgba(74, 144, 226, 0.3);
        }
        
        .collapsible {
            cursor: pointer;
            user-select: none;
        }
        
        .collapsible:hover {
            background: rgba(102, 126, 234, 0.1);
        }
        
        .order-content {
            display: none;
            animation: slideDown 0.3s ease;
        }
        
        .order-content.active {
            display: block;
        }
        
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Hyperliquid Trading Interface</h1>
            <p>Professional trading dashboard for Hyperliquid DEX</p>
        </div>

        <div class="main-content">
            <div class="control-panel">
                <h2>⚡ Control Panel</h2>
                
                <div class="form-group">
                    <label>Select Wallet:</label>
                    <div class="radio-group">
                        <label>
                            <input type="radio" name="wallet" value="ledger" checked>
                            📱 Ledger
                        </label>
                        <label>
                            <input type="radio" name="wallet" value="trade">
                            💼 Trade Wallet
                        </label>
                        <label>
                            <input type="radio" name="wallet" value="dex">
                            🏦 DEX Wallet
                        </label>
                    </div>
                </div>

                <div class="form-group">
                    <label for="customAddress">Custom Address:</label>
                    <input type="text" id="customAddress" placeholder="0x..." />
                </div>

                <div class="form-group">
                    <label>Actions:</label>
                    <button class="btn" onclick="getOpenOrders()">📋 Get Open Orders</button>
                    <button class="btn secondary" onclick="getAccountInfo()">💰 Get Portfolio Value</button>
                    
                    <!-- Collapsible Make Order Section -->
                    <button class="btn place-order collapsible" onclick="toggleOrderForm()">🎯 Make Order</button>
                    
                    <div class="order-content" id="orderContent">
                        <div class="order-form">
                            <h3>📈 Place New Order</h3>
                            
                            <div class="order-type-group">
                                <label class="buy-order">
                                    <input type="radio" name="orderType" value="buy" checked>
                                    <span>🟢 BUY</span>
                                </label>
                                <label class="sell-order">
                                    <input type="radio" name="orderType" value="sell">
                                    <span>🔴 SELL</span>
                                </label>
                            </div>
                            
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="coinSelect">Coin:</label>
                                    <select id="coinSelect">
                                        <option value="@153">FUSD</option>
                                        <option value="@166">USDT0</option>
                                        <option value="@180">USDHL</option>
                                        <option value="@107">HYPE</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label for="orderSize">Size:</label>
                                    <input type="number" id="orderSize" placeholder="50" step="0.01" min="0.01">
                                </div>
                            </div>
                            
                            <div class="form-group">
                                <label for="orderPrice">Price:</label>
                                <input type="number" id="orderPrice" placeholder="1.001" step="0.001" min="0.001">
                            </div>
                            
                            <button class="btn place-order" onclick="placeOrder()">⚡ Place Order</button>
                        </div>
                    </div>
                    
                    <button class="btn danger" onclick="clearResults()">🗑️ Clear Results</button>
                </div>
            </div>

            <div class="results-panel">
                <h2>📈 Results</h2>
                <div class="loading" id="loading">Loading data...</div>
                <div class="results-content" id="results">
Welcome to Hyperliquid Trading Interface! 🎉
================================================

Default Addresses:
🏦 Ledger: {{ ledger_address }}
💼 Trade Wallet: {{ trade_wallet }}
🏦 DEX Wallet: {{ dex_wallet }}

Ready to trade! Select an action to begin...
                </div>
            </div>
        </div>

        <div class="status-bar">
            <span id="status">Ready to trade ✨</span>
        </div>
    </div>

    <script>
        const LEDGER_ADDRESS = '{{ ledger_address }}';
        const TRADE_WALLET = '{{ trade_wallet }}';
        const DEX_WALLET = '{{ dex_wallet }}';
        
        function updateStatus(message) {
            document.getElementById('status').textContent = new Date().toLocaleTimeString() + ' - ' + message;
        }

        function showLoading() {
            document.getElementById('loading').style.display = 'block';
            document.getElementById('results').style.display = 'none';
        }

        function hideLoading() {
            document.getElementById('loading').style.display = 'none';
            document.getElementById('results').style.display = 'block';
        }

        function appendResults(text) {
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML += text;
            resultsDiv.scrollTop = resultsDiv.scrollHeight;
        }

        function setResults(text) {
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = text;
            resultsDiv.scrollTop = resultsDiv.scrollHeight;
        }

        function clearResults() {
            document.getElementById('results').innerHTML = '';
            updateStatus('Results cleared 🧹');
        }

        function toggleOrderForm() {
            const orderContent = document.getElementById('orderContent');
            orderContent.classList.toggle('active');
        }

        function getCurrentAddress() {
            const customAddress = document.getElementById('customAddress').value.trim();
            if (customAddress) {
                return customAddress;
            }
            
            const selectedWallet = document.querySelector('input[name="wallet"]:checked').value;
            if (selectedWallet === 'ledger') return LEDGER_ADDRESS;
            if (selectedWallet === 'trade') return TRADE_WALLET;
            if (selectedWallet === 'dex') return DEX_WALLET;
            return LEDGER_ADDRESS;
        }

        async function makeRequest(endpoint, address) {
            showLoading();
            try {
                const response = await fetch(`/${endpoint}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ address: address })
                });
                
                const data = await response.json();
                hideLoading();
                return data;
            } catch (error) {
                hideLoading();
                return { success: false, error: 'Network error: ' + error.message };
            }
        }

        async function placeOrder() {
            const coin = document.getElementById('coinSelect').value;
            const size = parseFloat(document.getElementById('orderSize').value);
            const price = parseFloat(document.getElementById('orderPrice').value);
            const orderType = document.querySelector('input[name="orderType"]:checked').value;
            const buy_or_sell = orderType === 'buy';
            
            // Validation
            if (!size || size <= 0) {
                alert('Please enter a valid size');
                return;
            }
            
            if (!price || price <= 0) {
                alert('Please enter a valid price');
                return;
            }
            
            const coinName = getCoinName(coin);
            const orderTypeText = buy_or_sell ? 'BUY' : 'SELL';
            
            if (!confirm(`Place ${orderTypeText} order for ${size} ${coinName} at $${price}?`)) {
                return;
            }
            
            updateStatus(`Placing ${orderTypeText} order for ${coinName}...`);
            appendResults(`\\n⚡ Placing ${orderTypeText} order for ${size} ${coinName} at $${price}...\\n`);
            
            try {
                showLoading();
                const response = await fetch('/make_order', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        coin: coin,
                        buy_or_sell: buy_or_sell,
                        size: size,
                        price: price
                    })
                });
                
                const result = await response.json();
                hideLoading();
                
                if (result.success) {
                    updateStatus(`✅ ${orderTypeText} order placed successfully`);
                    appendResults(`<pre>✅ ${orderTypeText} Order Placed Successfully!\\nResult: ${JSON.stringify(result.data, null, 2)}\\n</pre>`);
                    
                    // Clear form
                    document.getElementById('orderSize').value = '';
                    document.getElementById('orderPrice').value = '';
                    
                    // Show success popup
                    alert(`✅ ${orderTypeText} order for ${size} ${coinName} placed successfully!`);
                } else {
                    updateStatus(`❌ Failed to place ${orderTypeText} order`);
                    appendResults(`<pre>❌ Error placing order: ${result.error}\\n</pre>`);
                    alert(`❌ Error placing order: ${result.error}`);
                }
            } catch (error) {
                hideLoading();
                updateStatus(`❌ Network error placing order`);
                appendResults(`<pre>❌ Network error: ${error.message}\\n</pre>`);
                alert(`❌ Network error: ${error.message}`);
            }
        }

        async function getOpenOrders() {
            const address = getCurrentAddress();
            updateStatus(`Fetching open orders for ${address.substring(0, 10)}...`);
            appendResults(`\\n🔍 Fetching open orders for: ${address}\\n`);
            
            const result = await makeRequest('get_open_orders', address);
            
            if (result.success) {
                setResults(result.data);
                updateStatus('✅ Open orders retrieved successfully');
            } else {
                appendResults(`<pre>❌ Error: ${result.error}\n</pre>`);
                updateStatus('❌ Error fetching open orders');
            }
        }

        async function getAccountInfo() {
            const address = getCurrentAddress();
            updateStatus(`Fetching portfolio info for ${address.substring(0, 10)}...`);
            appendResults(`\\n💰 Fetching portfolio info for: ${address}\\n`);
            
            const result = await makeRequest('get_account_info', address);
            
            if (result.success) {
                setResults(result.data);
                updateStatus('✅ Portfolio info retrieved successfully');
            } else {
                appendResults(`<pre>❌ Error: ${result.error}\n</pre>`);
                updateStatus('❌ Error fetching portfolio info');
            }
        }

        async function cancelOrder(coin_symbol, oid) {
            // Get the friendly name for display purposes
            const coin_name = getCoinName(coin_symbol);
            
            if (!confirm(`Are you sure you want to cancel this ${coin_name} order?`)) {
                return;
            }
            
            updateStatus(`Cancelling ${coin_name} order...`);
            
            try {
                const response = await fetch('/cancel_order', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        coin: coin_symbol,  // Pass the original symbol (@153, @166, etc.)
                        oid: oid
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    updateStatus(`✅ ${coin_name} order cancelled successfully`);
                    // Show popup message
                    alert(`✅ ${coin_name} order cancelled successfully!`);
                    // Refresh open orders automatically
                    setTimeout(() => getOpenOrders(), 1000);
                } else {
                    updateStatus(`❌ Failed to cancel ${coin_name} order`);
                    alert(`❌ Error cancelling ${coin_name} order: ${result.error}`);
                }
            } catch (error) {
                updateStatus(`❌ Network error cancelling order`);
                alert(`❌ Network error: ${error.message}`);
            }
        }

        function getCoinName(symbol) {
            const symbolToCoin = {
                "@153": "FUSD",
                "@166": "USDT0", 
                "@180": "USDHL",
                "@107": "HYPE"
            };
            return symbolToCoin[symbol] || symbol;
        }
    </script>
</body>
</html>
    """
    
    return render_template_string(html_template, 
                                ledger_address=LEDGER_ADDRESS, 
                                trade_wallet=TRADE_WALLET,
                                dex_wallet=DEX_WALLET)

@app.route('/get_open_orders', methods=['POST'])
def api_get_open_orders():
    """API endpoint for getting open orders"""
    try:
        data = request.json
        address = data.get('address')
        
        if not address:
            return jsonify({'success': False, 'error': 'Address is required'})
        
        orders, has_orders, error = get_open_orders(address)
        
        if error:
            return jsonify({'success': False, 'error': error})
        
        if has_orders:
            result_text = f"<pre>Found {len(orders)} open order(s):\n"
            result_text += "=" * 50 + "\n\n"
            
            for i, order in enumerate(orders, 1):
                coin_symbol = order.get('coin', 'N/A')
                coin_name = get_coin(coin_symbol)
                oid = order.get('oid', 'N/A')
                side = order.get('side', 'N/A')
                side_text = "(Buy order)" if side == "B" else "(Sell order)" if side == "A" else ""
                
                result_text += f"📋 Order #{i}:\n"
                result_text += f"  🪙 Symbol: {coin_symbol} ({coin_name})\n"
                result_text += f"  📈 Side: {side} {side_text}\n"
                result_text += f"  📏 Size: {order.get('sz', 'N/A')}\n"
                result_text += f"  💰 Price: {order.get('limitPx', 'N/A')}\n"
                result_text += f"  🆔 Order ID: {oid}\n"
                result_text += f"  ⏰ Timestamp: {order.get('timestamp', 'N/A')}\n"
                result_text += f"  🗑️ Action: </pre><button class='cancel-btn' onclick='cancelOrder(\"{coin_symbol}\", \"{oid}\")'>Cancel Order</button><pre>\n"
                result_text += "-" * 30 + "\n"
            
            result_text += "</pre>"
        else:
            result_text = "<pre>📭 No open orders found.\n</pre>"
        
        return jsonify({'success': True, 'data': result_text})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})

@app.route('/get_account_info', methods=['POST'])
def api_get_account_info():
    """API endpoint for getting account info with spot balances and portfolio values"""
    try:
        data = request.json
        address = data.get('address')
        
        if not address:
            return jsonify({'success': False, 'error': 'Address is required'})
        
        # Get spot balances
        spot_balances = get_spot_asset_balances(address)
        
        if spot_balances is None:
            return jsonify({'success': False, 'error': 'Failed to fetch spot balances'})
        
        # Format the balances with values for display
        formatted_balances = format_spot_balances_with_values(spot_balances, address)
        
        return jsonify({'success': True, 'data': formatted_balances})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'})

@app.route('/make_order', methods=['POST'])
def api_make_order():
    """API endpoint for making an order"""
    try:
        data = request.json
        coin = data.get('coin')  # This will be @153, @166, etc.
        buy_or_sell = data.get('buy_or_sell')  # True for buy, False for sell
        size = data.get('size')
        price = data.get('price')
        
        print(f"DEBUG: Received order request - Coin: '{coin}', Buy: {buy_or_sell}, Size: {size}, Price: {price}")
        print(f"DEBUG: Request data: {data}")
        
        # Validation
        if coin is None or buy_or_sell is None or size is None or price is None:
            return jsonify({'success': False, 'error': 'All fields (coin, buy_or_sell, size, price) are required'})
        
        try:
            size = float(size)
            price = float(price)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Size and price must be valid numbers'})
        
        if size <= 0 or price <= 0:
            return jsonify({'success': False, 'error': 'Size and price must be greater than 0'})
        
        # Place the order
        order_result = run_async_make_order(coin, buy_or_sell, size, price)
        
        if order_result is not None:
            return jsonify({'success': True, 'data': order_result})
        else:
            return jsonify({'success': False, 'error': 'Failed to place order after multiple retries'})
        
    except Exception as e:
        error_msg = f'Server error: {str(e)}'
        print(f"DEBUG: Exception in api_make_order: {error_msg}")
        return jsonify({'success': False, 'error': error_msg})

@app.route('/cancel_order', methods=['POST'])
def api_cancel_order():
    """API endpoint for cancelling an order"""
    try:
        data = request.json
        coin = data.get('coin')  # This will be @153, @166, etc.
        oid = data.get('oid')
        
        print(f"DEBUG: Received cancel request - Coin: '{coin}', OID: '{oid}'")
        print(f"DEBUG: Request data: {data}")
        
        if not all([coin, oid]):
            return jsonify({'success': False, 'error': 'Both coin and oid are required'})
        
        success, result = run_async_cancel(coin, oid)
        
        if success:
            return jsonify({'success': True, 'data': result})
        else:
            return jsonify({'success': False, 'error': result})
        
    except Exception as e:
        error_msg = f'Server error: {str(e)}'
        print(f"DEBUG: Exception in api_cancel_order: {error_msg}")
        return jsonify({'success': False, 'error': error_msg})

if __name__ == '__main__':
    print("🚀 Starting Hyperliquid Trading Interface...")
    print("📱 Open your browser and go to: http://localhost:5000")
    print("🛑 Press Ctrl+C to stop the server")
    app.run(debug=True, host='0.0.0.0', port=5000)
