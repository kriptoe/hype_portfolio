import requests
import time
import csv
import json
from datetime import datetime, timedelta
from utils import get_asset_price
from web3 import Web3
# Define the API endpoint
url = "https://api.hyperliquid.xyz/info"
rpc="https://rpc.hyperliquid.xyz/evm"

KHYPE_PRICE = 1.015  # kHYPE to HYPE conversion rate
# Replace with your on-chain wallet address
user_address = "0x2a21Cc5D8Bcaa0D10078C99606B03Ee46C58817d" #"0x87d1910BE2AaE6D9C22F15AC9009Ec8Ca8706BAd"
DEX_WALLET = "0x62E485fD0e5c7D32f8cCF11aa356A1179C76e400"
LEDGER ="0x87d1910BE2AaE6D9C22F15AC9009Ec8Ca8706BAd"
OG = "0xE90Eee57653633E7558838b98F543079649c9C2F"
RABBY ="0x51ede09a0F69CCAe442a63b2633Ca50eFd47c15F"
SUPER ="0x918b7bA1A1e2035295AF9b13c6613dbf199C4C4d"
NEGOTIONE = "0xe0f6DAcd86734Ea6fAa476565eD923Daac521064"
TOUCH = "0x3a8003600363040D3863077F61e20Bd01787786f"
    #Fetches info about an accounts perps position on Hyperliquid.
    #Args:user_address (str): The user's on-chain wallet address.

totalStaked = 0

def get_perps_account_value(user_address):
    # Define the request payload
    payload = {
        "type": "clearinghouseState",
        "user": user_address
    }

    # Define headers
    headers = {
        "Content-Type": "application/json"
    }

    try:
        # Send the POST request
        response = requests.post(url, json=payload, headers=headers)
        
        # Check if the response was successful
        if response.status_code == 200:
            data = response.json()
            
            # Extract account value
            account_value = data.get('crossMarginSummary', {}).get('accountValue', "N/A")
            return(account_value)

    except Exception as e:
        print(f"An error occurred retrieving perps account value: {e}")
        return 0


def get_user_fills(user_address, days_back, api_url="https://api.hyperliquid.xyz/info"):
    """
    Retrieves and prints all user fills (trades) for the past x days from Hyperliquid API.
    Also returns an array of unique coin names with their most recent trade side.

    Args:
        user_address (str): User's address in 42-character hexadecimal format (e.g., '0x000...').
        days_back (int): Number of days in the past to fetch fills for.
        api_url (str): The Hyperliquid API endpoint URL (default: 'https://api.hyperliquid.xyz/info').

    Returns:
        list: Array of tuples with (coin symbol, side) (e.g., [('XRP', 'Buy'), ('BTC', 'Sell')]).
    """

    # Calculate start and end timestamps in milliseconds
    end_time = int(time.time() * 1000)  # Current time in milliseconds
    start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)

    # Headers for the API request
    headers = {
        "Content-Type": "application/json"
    }

    # Initialize variables for pagination
    all_fills = []
    coin_side_map = {}  # Dictionary to store the most recent side for each coin
    has_more_fills = True

    while has_more_fills:
        # Request body for the API
        request_body = {
            "type": "userFillsByTime",
            "user": user_address,
            "startTime": start_time,
            "endTime": end_time
        }

        try:
            # Make the POST request to the API
            response = requests.post(api_url, headers=headers, json=request_body)
            response.raise_for_status()  # Raise an exception for bad status codes

            # Parse the response
            fills_data = response.json()

            if not fills_data:  # If no fills are returned, stop the loop
                has_more_fills = False
                break

            # Add the fills to the list
            all_fills.extend(fills_data)

            # Update the coin_side_map with the most recent side for each coin
            for fill in fills_data:
                coin = fill['coin']
                side = 'Buy' if fill['side'] == 'B' else 'Sell'
                # Update the map if this fill is newer than the existing one
                if coin not in coin_side_map or fill['time'] > coin_side_map[coin][1]:
                    coin_side_map[coin] = (side, fill['time'])

            # Check if we've received fewer than 2000 fills (indicating no more data)
            if len(fills_data) < 2000:
                has_more_fills = False
            else:
                # Update the end_time to the timestamp of the last fill to paginate
                end_time = fills_data[-1]["time"] - 1  # Subtract 1ms to avoid overlap

        except requests.exceptions.RequestException as e:
            print(f"Error fetching fills: {e}")
            break

    # Print the fills in a readable format
    if all_fills:
        print(f"\nFound {len(all_fills)} fills for user {user_address} from {days_back} days ago to now:")

    else:
        print(f"No fills found for user {user_address} in the past {days_back} days.")

    # Convert the coin_side_map to a list of tuples (coin, side) and return
    coin_side_list = [(coin, side) for coin, (side, _) in coin_side_map.items()]
    return coin_side_list


def get_address_positions(address):
    # API endpoint
    url = "https://api.hyperliquid.xyz/info"
    
    # Headers
    headers = {
        "Content-Type": "application/json"
    }
    
    # Request body
    payload = {
        "type": "clearinghouseState",
        "user": address
    }
    
    try:
        # Make POST request
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
            
            # Print formatted position information
            print(f"Positions for address: {address}")
            print("-" * 50)
            
            # Print asset positions
            if "assetPositions" in data and data["assetPositions"]:
                for pos in data["assetPositions"]:
                    position = pos["position"]
                    print(f"Coin: {position['coin']}")
                    print(f"Size: {position['szi']}")
                    print(f"Entry Price: ${position['entryPx']}")
                    print(f"Leverage: {position['leverage']['value']}x")
                    print(f"Position Value: ${position['positionValue']}")
                    print(f"Unrealized PnL: ${position['unrealizedPnl']}")
                    print(f"Margin Used: ${position['marginUsed']}")
                    print(f"Liquidation Price: ${position['liquidationPx']}")
                    print("-" * 50)
            
            # Print margin summary
            if "marginSummary" in data:
                margin = data["marginSummary"]
                print("Margin Summary:")
                print(f"Account Value: ${margin['accountValue']}")
                print(f"Total Margin Used: ${margin['totalMarginUsed']}")
                print(f"Total Notional Position: ${margin['totalNtlPos']}")
                print(f"Total Raw USD: ${margin['totalRawUsd']}")
                
            # Print withdrawable amount
            if "withdrawable" in data:
                print(f"Withdrawable: ${data['withdrawable']}")
                
        else:
            print(f"Error: Received status code {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {str(e)}")
    except json.JSONDecodeError:
        print("Error: Invalid JSON response received")
    except KeyError as e:
        print(f"Error: Missing expected data field: {str(e)}")


def get_funding_history(user_address, days=7):
    """
    Fetches and prints the user's funding history in a readable format.

    Args:
        user_address (str): The user's on-chain wallet address.
        days (int): Number of past days to fetch data for (default is 7).
    """

    # API endpoint
    url = "https://api.hyperliquid.xyz/info"

    # Time range: past `days` days
    start_time = int(time.time() * 1000) - (days * 24 * 60 * 60 * 1000)
    end_time = int(time.time() * 1000)

    # Request payload
    payload = {
        "type": "userFunding",
        "user": user_address,
        "startTime": start_time,
        "endTime": end_time
    }

    # Headers
    headers = {"Content-Type": "application/json"}

    # Send request
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        funding_data = response.json()
        total_funding = 0

        # Print formatted funding history
        print("\nFunding History:\n" + "-" * 50)
        for entry in funding_data:
            timestamp = datetime.utcfromtimestamp(entry["time"] / 1000).strftime('%Y-%m-%d %H:%M:%S UTC')
            coin = entry["delta"]["coin"]
            funding_rate = entry["delta"]["fundingRate"]
            usdc = entry["delta"]["usdc"]
            szi = entry["delta"]["szi"]

            total_funding += float(usdc)

            print(f"Time: {timestamp}")
            print(f"  Funding Rate: {funding_rate} = {round(float(funding_rate) * 24 * 365* 100,1)}%")
            print(f"  USDC Change: {usdc}")
            print(f"  Position Size: {szi}")
            print("-" * 50)
    else:
        print(f"Error: {response.status_code}, {response.text}")
    return total_funding


def get_historical_funding_rates(coin="HYPE", days=7, output_file="funding_rates.csv"):
    """
    Fetches historical funding rates for the given coin and saves to a CSV file.

    Args:
        coin (str): The coin to fetch funding rates for (default: "HYPE").
        days (int): Number of past days to fetch data for (default: 7).
        output_file (str): Name of the CSV file to save data to (default: "funding_rates.csv").
    """

    # API endpoint
    url = "https://api.hyperliquid.xyz/info"

    # Time range: past `days` days
    start_time = int(time.time() * 1000) - (days * 24 * 60 * 60 * 1000)
    end_time = int(time.time() * 1000)

    # Request payload
    payload = {
        "type": "fundingHistory",
        "coin": coin,
        "startTime": start_time,
        "endTime": end_time
    }

    # Headers
    headers = {"Content-Type": "application/json"}

    # Send request
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        funding_data = response.json()

        # Open CSV file for writing
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['time', 'funding_rate', 'premium']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header
            writer.writeheader()
            
            # Write data rows
            for entry in funding_data:
                timestamp = datetime.utcfromtimestamp(entry["time"] / 1000).strftime('%Y-%m-%d %H:%M:%S UTC')
                writer.writerow({
                    'time': timestamp,
                    'funding_rate': entry["fundingRate"],
                    'premium': entry["premium"]
                })
        
        print(f"Data successfully saved to {output_file}")
        
        # Print formatted funding rate history (optional, can be removed)
        print(f"\nHistorical Funding Rates for {coin}:\n" + "-" * 50)
        for entry in funding_data:
            timestamp = datetime.utcfromtimestamp(entry["time"] / 1000).strftime('%Y-%m-%d %H:%M:%S UTC')
            funding_rate = entry["fundingRate"]
            premium = entry["premium"]

            print(f"Time: {timestamp}")
            print(f"  Funding Rate: {funding_rate}")
            print(f"  Premium: {premium}")
            print("-" * 50)
    else:
        print(f"Error: {response.status_code}, {response.text}")


def get_open_orders(user_address):
    url = "https://api.hyperliquid.xyz/info"
    headers = {"Content-Type": "application/json"}
    payload = {"type": "frontendOpenOrders", "user": user_address}
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching open orders: {e}")
        return None


       

def get_token_balance(wallet_address, token_name, api_url="https://api.hyperliquid.xyz/info"):
    """
    Retrieves the balance of a specified token and USDC for a given wallet address.
    
    Args:
        wallet_address (str): The wallet address to check (42-character hexadecimal format)
        token_name (str): The name of the token to check (e.g., 'HYPE', 'HFUN', 'USDC')
        api_url (str): The Hyperliquid API endpoint URL
    
    Returns:
        tuple: (token_balance, usdc_balance) as floats, or (None, None) if there's an error
    """
    try:
        # Prepare the API request payload for spotClearinghouseState
        payload = {
            "type": "spotClearinghouseState",
            "user": wallet_address
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Make the API request
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        # Initialize balances
        token_balance = None
        usdc_balance = None
        
        # Find the balances in the response
        for balance in data.get('balances', []):
            coin_name = balance['coin'].upper()
            if coin_name == token_name.upper():  # Case-insensitive comparison for requested token
                token_balance = float(balance['total'])
            if coin_name == 'USDC':  # Always check for USDC
                usdc_balance = float(balance['total'])
        
        # Handle case where token balance isn't found
        if token_balance is None:
            # print(f"No {token_name} balance found for wallet {wallet_address}")
            token_balance = 0.0
        
        # Handle case where USDC balance isn't found
        if usdc_balance is None:
            print(f"No USDC balance found for wallet {wallet_address}")
            usdc_balance = 0.0
        
        return token_balance, usdc_balance

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None, None
    except json.JSONDecodeError as e:
        print(f"Failed to parse API response: {e}")
        return None, None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, None


def get_account_balances(wallet_addresses, token_name="HYPE", wallet_labels=None):
    """
    Gets the SPOT account balances of a specified token and USDC for multiple wallets.
    
    Args:
        wallet_addresses (tuple): A tuple of wallet addresses to check
        token_name (str): The name of the token to check (default: 'HYPE')
        wallet_labels (tuple): Optional tuple of labels for each wallet (e.g., 'TRADE', 'DEX', 'LEDGER')
    
    Returns:
        tuple: (total_token_balance, total_usdc_balance) as floats, or (None, None) if there's an error
    """
    if not wallet_addresses:
        print("Error: No wallet addresses provided")
        return None, None

    if wallet_labels and len(wallet_labels) != len(wallet_addresses):
        print("Error: Number of wallet labels must match number of wallet addresses")
        return None, None
    
    global totalStaked
    running_token_balance = 0
    running_usdc_balance = 0
    running_perps_balance = 0
    error_occurred = False

    # Use labels if provided, otherwise use generic numbering
    labels = wallet_labels if wallet_labels else [f"Wallet {i+1}" for i in range(len(wallet_addresses))]

    for wallet_address, label in zip(wallet_addresses, labels):
        balance, usdc_balance = get_token_balance(wallet_address, token_name)
        
        if balance is None or usdc_balance is None:
            print(f"Skipping wallet {label} ({wallet_address}) due to API error")
            error_occurred = True
            continue

        perps = float(get_perps_account_value(wallet_address))
        running_token_balance += balance
        running_usdc_balance += usdc_balance
        running_perps_balance += perps
        print(f"{token_name} balance for {label} wallet {wallet_address[:5]}...: {balance:.0f} {token_name} "
            f"USDC Balance ${usdc_balance:,.0f} Perps Balance ${perps:,.0f}")

    if error_occurred:
        print("Warning: Some wallet balances could not be retrieved due to errors")

    # Note: I've kept the +60200 from your original code, but you might want to explain what this represents
    print(f"Total {token_name}: {running_token_balance + totalStaked:,.0f}")
    print(f"Total SPOT USDC: {running_usdc_balance:,.0f}")
    print(f"Total Perps: {running_perps_balance:,.0f}")
    print(f"Total USDC: {running_perps_balance + running_usdc_balance:,.0f}")
    print(f"Total Other Stables: {other_stables:,.0f}")    
    return running_token_balance, running_usdc_balance


def get_staking_amount(wallet_address, api_url="https://api.hyperliquid.xyz/info"):
    """
    Retrieves the staking (delegated) amount for a given wallet address.
    
    Args:
        wallet_address (str): The wallet address to check (42-character hexadecimal format)
        api_url (str): The Hyperliquid API endpoint URL
    
    Returns:
        float: The delegated (staked) amount, or None if there's an error
    """
    try:
        # Prepare the API request payload for delegatorSummary
        payload = {
            "type": "delegatorSummary",
            "user": wallet_address
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Make the API request
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Extract the delegated (staked) amount
        delegated_amount = float(data.get('delegated', 0.0))
        
        if delegated_amount == 0.0:
            print(f"No staking amount found for wallet {wallet_address}")
        
        return delegated_amount

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse API response: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_eth_balance(wallet_address, rpc_url):
    """
    Retrieves the ETH balance of a wallet address using the eth_getBalance RPC endpoint.
    
    Args:
        wallet_address (str): The wallet address to check (42-character hexadecimal format)
        rpc_url (str): The RPC endpoint URL
    
    Returns:
        float: The ETH balance in Ether, or None if there's an error
    """
    try:
        # Prepare the RPC request payload
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getBalance",
            "params": [wallet_address, "latest"],
            "id": 1
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Make the RPC request
        response = requests.post(rpc_url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Check for RPC errors
        if "error" in data:
            print(f"RPC error: {data['error']['message']}")
            return None
        
        # Extract the balance in Wei (hexadecimal)
        balance_wei = int(data["result"], 16)
        
        # Convert Wei to Ether (1 ETH = 10^18 Wei)
        balance_eth = balance_wei / 10**18
        
        return balance_eth

    except requests.exceptions.RequestException as e:
        print(f"RPC request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse RPC response: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_native_hype_balance(user_address):
    """
    Get the native HYPE balance for a specific user address on HyperEVM.
    
    Args:
        user_address: The wallet address to check balance for
        
    Returns:
        tuple: (balance_wei, balance_hype)
    """
    RPC_URL = "https://rpc.hyperliquid.xyz/evm"
    
    # Connect to the RPC
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Check connection
    if not w3.is_connected():
        raise Exception("Failed to connect to RPC")
    
    # Get native balance in wei (smallest unit)
    balance_wei = w3.eth.get_balance(Web3.to_checksum_address(user_address))
    
    # HYPE has 18 decimals (standard for native tokens)
    decimals = 18
    
    # Convert to human-readable format
    balance_hype = balance_wei / (10 ** decimals)
    
    return balance_wei, balance_hype


def get_evm_balances():
    """
    Retrieves the EVM Hype balances using the RPC Endpoint.
    https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/hyperevm/json-rpc
    """    
    for wallet_address, label in zip(wallet_addresses, wallet_labels):
        print(f"EVM ETH Balance for {label} wallet {wallet_address}: {get_eth_balance(wallet_address, rpc):.6f} ETH")


def getHype():
    global totalStaked
    """
    Gets the total Hype I have over multiple wallets on Hypercore
    
    """
    stake_amount = get_staking_amount(user_address)
    totalStaked = totalStaked + stake_amount
    print(f"Staked Hype for {user_address} {stake_amount:,.0f}")
    stake_amount = get_staking_amount(TOUCH)
    print(f"Staked Hype for {TOUCH} {stake_amount:,.0f}")
    totalStaked = totalStaked + stake_amount
    stake_amount = get_staking_amount(DEX_WALLET)
    totalStaked = totalStaked + stake_amount
    print(f"Staked Hype for {DEX_WALLET} {stake_amount:,.0f}")
    stake_amount = get_staking_amount(SUPER)
    totalStaked = totalStaked + stake_amount
    print(f"Staked Hype for {SUPER} {stake_amount:,.0f}")
    stake_amount = get_staking_amount(LEDGER)
    totalStaked = totalStaked + stake_amount
    print(f"Staked Hype for {LEDGER} {stake_amount:,.0f}")    
        # Get balances
    print("Hypercore HYPE balances")
    total_hype, total_usdc = get_account_balances(wallet_addresses, token_name="HYPE", wallet_labels=wallet_labels)

    if total_hype is not None and total_usdc is not None:
        print(f"\nHYPERCORE totals retrieved successfully:")
        print(f"Hypercore Total {total_hype + totalStaked:,.0f} HYPE - includes staking of ({totalStaked:,.0f})")
        print(f"Total {total_usdc:,.0f} USDC")
        print(f"Total {other_stables:,.0f} NON USDC Stables")
        print(f"Total STAKED {totalStaked:,.0f} HYPE")

    # --- NEW: kHYPE queued for unstaking ---
    print("\nChecking kHYPE unstaking queues...")
    total_queued_khype = 0.0
    for wallet_address, label in zip(wallet_addresses, wallet_labels):
        queued, details = get_khype_queued_withdrawals(wallet_address, label)
        total_queued_khype += queued

    print(f"\nTotal kHYPE in unstaking queue (all wallets): {total_queued_khype:,.4f}")

    # ... your existing get_account_balances call ...

    # Add queued kHYPE to your total
    print(f"Hypercore Total {total_hype + totalStaked + total_queued_khype:,.0f} HYPE "
          f"(includes {total_queued_khype:,.0f} queued for unstake)")
    return total_queued_khype, total_hype   

def get_stablecoins_balances(token_name):
    wallet_addresses_L1 = (user_address, DEX_WALLET, OG, LEDGER)
    wallet_labels = ("TRADE", "DEX","0x8", "LEDGER")
        # Use labels if provided, otherwise use generic numbering
    labels = wallet_labels if wallet_labels else [f"Wallet {i+1}" for i in range(len(wallet_addresses))]


    total_stables = 0
    for wallet_address, label in zip(wallet_addresses_L1, labels):
        balance, usdc_balance = get_token_balance(wallet_address, token_name)
        total_stables=total_stables + balance    
        if balance is None or usdc_balance is None:
            print(f"Skipping wallet {label} ({wallet_address}) due to API error")
            error_occurred = True
            continue

        perps = float(get_perps_account_value(wallet_address))
        #print(f"{token_name} balance for {label} wallet {wallet_address[:5]}...: {balance:.0f} {token_name} ")


    print(f"Total {token_name} : ${total_stables}")
    return total_stables


wallet_addresses = (user_address, DEX_WALLET, LEDGER, RABBY,  SUPER, OG, TOUCH)
wallet_labels = ("TRADE", "DEX", "LEDGER", "RABBY",  "SUPER", "0x8", "Ledger Touch")

other_stables=0
feusd_balance = get_stablecoins_balances("FEUSD")
if feusd_balance is not None:
    other_stables += feusd_balance

usdhl_balance = get_stablecoins_balances("USDHL")
if usdhl_balance is not None:
    other_stables += usdhl_balance

usdt_balance = get_stablecoins_balances("USDT0")
if usdt_balance is not None:
    other_stables += usdt_balance

days = 7

# detects any KHYPE that is in the unstaking phase
def get_khype_queued_withdrawals(wallet_address, label="wallet"):
    """
    Uses HyperEVMScan API to find queueWithdrawal txs in the last 9 days,
    then verifies which are still pending via eth_call.
    """
    RPC_URL = "https://rpc.hyperliquid.xyz/evm"
    STAKING_MANAGER = "0x393D0B87Ed38fc779FD9611144aE649BA6082109"
    EVMSCAN_API = "https://api.etherscan.io/v2/api"
    QUEUE_METHOD_ID = "0x6b174f35"

    w3 = Web3(Web3.HTTPProvider(RPC_URL))

    # Fetch last 9 days of txs from HyperEVMScan
    nine_days_ago = int(time.time()) - (9 * 24 * 3600)

    params = {
        "chainid": 999,  # HyperEVM chain ID
        "module": "account",
        "action": "txlist",
        "address": wallet_address,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": "IZDY1JPGEZEYRYI1XSKZ1VVB6IC4E88Y16"
    }

    try:
        resp = requests.get(EVMSCAN_API, params=params)
        txs = resp.json().get("result", [])
        txs = resp.json().get("result", [])
        if not isinstance(txs, list):
            print(f"  API error for {label}: {txs}")
            return 0, []
        
    except Exception as e:
        print(f"  API error for {label}: {e}")
        return 0, []

    # Filter: to staking manager, correct method, within 9 days
    withdrawal_ids = []
    for tx in txs:
        if int(tx.get("timeStamp", 0)) < nine_days_ago:
            break  # sorted desc, so we can stop early
        if (tx.get("to", "").lower() == STAKING_MANAGER.lower()
                and tx.get("input", "").startswith(QUEUE_METHOD_ID)
                and tx.get("isError", "1") == "0"):
            # Decode withdrawalId from the WithdrawalQueued receipt log instead,
            # but we can also just check all IDs via eth_call below.
            # Extract kHYPE amount from input (first param after method ID)
            withdrawal_ids.append(tx["hash"])

    if not withdrawal_ids:
        return 0, []

    # For each tx, get the withdrawalId from the tx receipt logs
    from eth_abi import encode as abi_encode
    selector = w3.keccak(text="withdrawalRequests(address,uint256)")[:4]
    WITHDRAWAL_QUEUED_TOPIC = "0xbf9e917c1f92e31fa45b297f9a8c22993a560478bbb765b3fc430d7fa62e083c"

    total_queued_khype = 0.0
    pending = []

    for tx_hash in withdrawal_ids:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            for log in receipt.logs:
                if log.topics[0].hex() == WITHDRAWAL_QUEUED_TOPIC[2:]:
                    wid = int(log.topics[3].hex(), 16)
                    raw = bytes(log.data)

                    khype_queued = int(raw[0:32].hex(), 16) / 10**18

                    # Verify still pending
                    call_data = selector + abi_encode(
                        ['address', 'uint256'],
                        [Web3.to_checksum_address(wallet_address), wid]
                    )
                    result = w3.eth.call({
                        'to': Web3.to_checksum_address(STAKING_MANAGER),
                        'data': '0x' + call_data.hex()
                    })
                    hype = int(raw[32:64].hex(), 16) / 10**18
                    fee  = int(raw[64:96].hex(), 16) / 10**18

                    if hype > 0:
                        total_queued_khype += khype_queued
                        pending.append({'id': wid, 'khype_amount': khype_queued, 'hype_amount': hype, 'fee_amount': fee})
                        print(f"  [{label}] Withdrawal #{wid}: {khype_queued:,.4f} kHYPE → {hype:,.4f} HYPE (fee: {fee:.4f})")
        except Exception as e:
            print(f"  Error checking tx {tx_hash}: {e}")

    if total_queued_khype > 0:
        print(f"  [{label}] Total kHYPE queued: {total_queued_khype:,.4f}")
    return total_queued_khype, pending


def get_erc20_balances_for_wallets(token_address, wallets):
    """
    Get the ERC20 token balance for multiple wallet addresses.
    
    Args:
        token_address: The ERC20 token contract address
        wallets: Dictionary of wallet names and addresses
        
    Returns:
        dict: Dictionary with wallet names as keys and tuples of (balance_wei, balance_tokens, decimals) as values
    """
    RPC_URL = "https://rpc.hyperliquid.xyz/evm"
    
    # Connect to the RPC
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Check connection
    if not w3.is_connected():
        raise Exception("Failed to connect to RPC")
    
    # ERC20 ABI for balanceOf and decimals functions
    erc20_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "name",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function"
        }
    ]
    
    # Create contract instance
    token_contract = w3.eth.contract(
        address=Web3.to_checksum_address(token_address),
        abi=erc20_abi
    )
    
    # Get token info (only once)
    try:
        decimals = token_contract.functions.decimals().call()
        symbol = token_contract.functions.symbol().call()
        name = token_contract.functions.name().call()
    except Exception as e:
        raise Exception(f"Failed to get token info: {str(e)}")
    
    # Dictionary to store results
    results = {}
    
    # Get balance for each wallet
    for wallet_name, wallet_address in wallets.items():
        try:
            # Get balance in wei (smallest unit)
            balance_wei = token_contract.functions.balanceOf(
                Web3.to_checksum_address(wallet_address)
            ).call()
            
            # Convert to human-readable format
            balance_tokens = balance_wei / (10 ** decimals)
            
            results[wallet_name] = {
                'balance_wei': balance_wei,
                'balance_tokens': balance_tokens,
                'decimals': decimals,
                'address': wallet_address
            }
            
        except Exception as e:
            results[wallet_name] = {
                'error': str(e),
                'address': wallet_address
            }
    
    return results, symbol, name, decimals

# get_address_positions(user_address)    # gets perps positions
total_queued_khype, hypercore_spot_hype = getHype()
# Define wallet addresses
wallets = {
    "DEX_WALLET": "0x62E485fD0e5c7D32f8cCF11aa356A1179C76e400",
    "LEDGER": "0x87d1910BE2AaE6D9C22F15AC9009Ec8Ca8706BAd",
    "OG": "0xE90Eee57653633E7558838b98F543079649c9C2F",
    "RABBY": "0x51ede09a0F69CCAe442a63b2633Ca50eFd47c15F",
    "TRADE": "0x2a21Cc5D8Bcaa0D10078C99606B03Ee46C58817d",
    "SUPER": "0x918b7bA1A1e2035295AF9b13c6613dbf199C4C4d",
    "NEGOTIONE" : "0xe0f6DAcd86734Ea6fAa476565eD923Daac521064"
}
# Display header
print("=" * 80)
print("HYPE EVM Balance Report")
print("=" * 80)
print()

# Store total
total_hype = 0

# Check balance for each wallet
for wallet_name, wallet_address in wallets.items():
    try:
        balance_wei, balance_hype = get_native_hype_balance(wallet_address)
        total_hype += balance_hype
        
        print(f"{wallet_name:12} | {wallet_address}")
        print(f"{'':12} | Balance: {balance_hype:,.6f} HYPE")
        print("-" * 80)
        
    except Exception as e:
        print(f"{wallet_name:12} | {wallet_address}")
        print(f"{'':12} | Error: {str(e)}")
        print("-" * 80)

print(f"Total EVM Hype : {total_hype} HYPE")

# Check WHYPE balances
whype_address = "0x5555555555555555555555555555555555555555"
try:
    # Get WHYPE balances for all wallets
    whype_results, whype_symbol, whype_name, whype_decimals = get_erc20_balances_for_wallets(whype_address, wallets)
    
    # Display header
    print()
    print("=" * 80)
    print(f"WHYPE Balance Report")
    print(f"Token: {whype_name} ({whype_symbol})")
    print(f"Contract: {whype_address}")
    print(f"Decimals: {whype_decimals}")
    print("=" * 80)
    print()
    
    # Calculate total
    total_whype = 0
    
    # Display individual balances
    for wallet_name, data in whype_results.items():
        if 'error' in data:
            print(f"{wallet_name:12} | {data['address']}")
            print(f"{'':12} | Error: {data['error']}")
            print("-" * 80)
        else:
            total_whype += data['balance_tokens']
            print(f"{wallet_name:12} | {data['address']}")
            print(f"{'':12} | Balance: {data['balance_tokens']:,.6f} {whype_symbol}")
            print("-" * 80)
    
    # Display total
    print()
    print("=" * 80)
    print(f"TOTAL WHYPE ACROSS ALL WALLETS: {total_whype:,.6f} {whype_symbol}")
    print("=" * 80)
    print()
    
except Exception as e:
    print(f"Error fetching WHYPE balances: {str(e)}")
    print()
    # Define wallet addresses

    
    # Example token address (replace with actual ERC20 token address)
khype_address = "0xfD739d4e423301CE9385c1fb8850539D657C296D"
    
try:
    # Get balances for all wallets
    results, symbol, name, decimals = get_erc20_balances_for_wallets(khype_address, wallets)
    
    # Display header
    print("=" * 80)
    print(f"ERC20 Token Balance Report")
    print(f"Token: {name} ({symbol})")
    print(f"Contract: {khype_address}")
    print(f"Decimals: {decimals}")
    print("=" * 80)
    print()
    
    # Calculate total
    total_tokens = 0
    
    # Display individual balances
    for wallet_name, data in results.items():
        if 'error' in data:
            print(f"{wallet_name:12} | {data['address']}")
            print(f"{'':12} | Error: {data['error']}")
            print("-" * 80)
        else:
            total_tokens += data['balance_tokens']
            
            print(f"{wallet_name:12} | {data['address']}")
            print(f"{'':12} | Balance: {data['balance_tokens']:,.6f} {symbol}")
            print("-" * 80)
    
    # Display total
    print()
    print("=" * 80)
    print(f"TOTAL ACROSS ALL WALLETS: {total_tokens:,.6f} {symbol}")
    print("=" * 80)
    
except Exception as e:
    print(f"Error: {str(e)}")

# Grand Total
print("\n" + "=" * 80)
print("GRAND TOTAL HYPE SUMMARY")
print("=" * 80)

khype_as_hype = total_tokens * KHYPE_PRICE
queued_as_hype = total_queued_khype * KHYPE_PRICE

print(f"Hypercore HYPE (spot):    {hypercore_spot_hype:>15,.4f} HYPE")
print(f"Hypercore HYPE (staked):  {totalStaked:>15,.4f} HYPE")
print(f"Native HYPE (EVM):        {total_hype:>15,.4f} HYPE")
print(f"WHYPE (EVM):              {total_whype:>15,.4f} HYPE")
print(f"kHYPE (held):             {total_tokens:>15,.4f} kHYPE  →  {khype_as_hype:,.4f} HYPE")
print(f"kHYPE (unstaking queue):  {total_queued_khype:>15,.4f} kHYPE  →  {queued_as_hype:,.4f} HYPE")
print("-" * 80)
grand_total = hypercore_spot_hype + totalStaked + total_hype + total_whype + khype_as_hype + queued_as_hype
print(f"GRAND TOTAL:              {grand_total:>15,.4f} HYPE")
print("=" * 80)
