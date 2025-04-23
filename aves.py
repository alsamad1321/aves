import streamlit as st
import pandas as pd
import hashlib
import time
import json
import os
from datetime import datetime
import random
import string

# File paths
USERS_FILE = "users.json"
TRANSACTIONS_FILE = "transactions.json"
WALLETS_FILE = "wallets.json"

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.current_user = None

# Helper functions
def load_data(file_path, default=None):
    if default is None:
        default = {}
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump(default, f)
        return default
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default

def save_data(data, file_path):
    with open(file_path, 'w') as f:
        json.dump(data, f)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_wallet_address():
    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    address = '0x' + ''.join(random.choice(chars) for _ in range(40))
    return address

def initialize_app():
    users = load_data(USERS_FILE)
    transactions = load_data(TRANSACTIONS_FILE, [])
    wallets = load_data(WALLETS_FILE)
    return users, transactions, wallets

# App UI components
def login_page():
    st.title("Crypto Payment System")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            if not username or not password:
                st.error("Please enter both username and password.")
                return
                
            users = load_data(USERS_FILE)
            
            if username not in users:
                st.error("User does not exist.")
                return
                
            if users[username]["password"] != hash_password(password):
                st.error("Incorrect password.")
                return
                
            st.session_state.authenticated = True
            st.session_state.current_user = username
            st.success("Login successful!")
            st.rerun()
    
    with tab2:
        new_username = st.text_input("Choose Username", key="register_username")
        new_password = st.text_input("Choose Password", type="password", key="register_password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        if st.button("Register"):
            if not new_username or not new_password or not confirm_password:
                st.error("Please fill in all fields.")
                return
                
            if new_password != confirm_password:
                st.error("Passwords do not match.")
                return
                
            users = load_data(USERS_FILE)
            
            if new_username in users:
                st.error("Username already exists.")
                return
                
            # Create user
            wallet_address = generate_wallet_address()
            users[new_username] = {
                "password": hash_password(new_password),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            save_data(users, USERS_FILE)
            
            # Create wallet
            wallets = load_data(WALLETS_FILE)
            wallets[new_username] = {
                "address": wallet_address,
                "balance": {"BTC": 0.0, "ETH": 0.0, "USDT": 0.0}
            }
            save_data(wallets, WALLETS_FILE)
            
            st.success("Registration successful! Please login.")

def dashboard():
    st.title(f"Hello, {st.session_state.current_user}!")
    
    users, transactions, wallets = initialize_app()
    user_wallet = wallets.get(st.session_state.current_user, {})
    
    tab1, tab2, tab3, tab4 = st.tabs(["Wallet", "Send", "Receive", "History"])
    
    with tab1:
        st.subheader("Your Wallet")
        wallet_address = user_wallet.get("address", "No wallet found")
        st.code(wallet_address, language=None)
        
        st.subheader("Balances")
        balances = user_wallet.get("balance", {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("BTC", f"{balances.get('BTC', 0):.8f}")
        with col2:
            st.metric("ETH", f"{balances.get('ETH', 0):.8f}")
        with col3:
            st.metric("USDT", f"{balances.get('USDT', 0):.2f}")
            
        # Add funds for demo purposes
        if st.button("Add Demo Funds"):
            for coin in ["BTC", "ETH", "USDT"]:
                if coin == "BTC":
                    wallets[st.session_state.current_user]["balance"][coin] += 0.1
                elif coin == "ETH":
                    wallets[st.session_state.current_user]["balance"][coin] += 1.0
                else:
                    wallets[st.session_state.current_user]["balance"][coin] += 100.0
            save_data(wallets, WALLETS_FILE)
            st.success("Demo funds added successfully!")
            st.rerun()
    
    with tab2:
        st.subheader("Send Crypto")
        recipient = st.text_input("Recipient Wallet Address")
        
        coin = st.selectbox("Select Coin", ["BTC", "ETH", "USDT"])
        amount = st.number_input(f"Amount ({coin})", min_value=0.0, format="%.8f" if coin in ["BTC", "ETH"] else "%.2f")
        
        if st.button("Send Transaction"):
            if not recipient:
                st.error("Please enter a recipient address.")
                return
                
            if amount <= 0:
                st.error("Please enter a valid amount.")
                return
                
            # Check if recipient exists (for demo purposes)
            recipient_exists = False
            recipient_username = None
            for username, wallet_data in wallets.items():
                if wallet_data.get("address") == recipient:
                    recipient_exists = True
                    recipient_username = username
                    break
                    
            if not recipient_exists:
                st.error("Recipient address not found.")
                return
                
            # Check balance
            if amount > user_wallet["balance"].get(coin, 0):
                st.error(f"Insufficient {coin} balance.")
                return
                
            # Process transaction
            tx_id = hashlib.sha256(f"{time.time()}{st.session_state.current_user}{recipient}{amount}".encode()).hexdigest()[:16]
            
            # Update sender balance
            wallets[st.session_state.current_user]["balance"][coin] -= amount
            
            # Update recipient balance
            wallets[recipient_username]["balance"][coin] += amount
            
            # Save transaction
            transactions = load_data(TRANSACTIONS_FILE, [])
            transactions.append({
                "id": tx_id,
                "from": st.session_state.current_user,
                "to": recipient_username,
                "from_address": user_wallet["address"],
                "to_address": recipient,
                "amount": amount,
                "coin": coin,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            save_data(transactions, TRANSACTIONS_FILE)
            save_data(wallets, WALLETS_FILE)
            
            st.success(f"Transaction successful! ID: {tx_id}")
            st.rerun()
    
    with tab3:
        st.subheader("Receive Crypto")
        st.info("Share your wallet address below to receive crypto")
        st.code(wallet_address, language=None)
        
        if st.button("Copy Address"):
            st.info("Address copied to clipboard")
    
    with tab4:
        st.subheader("Transaction History")
        
        all_transactions = load_data(TRANSACTIONS_FILE, [])
        user_transactions = [tx for tx in all_transactions if 
                            tx.get("from") == st.session_state.current_user or 
                            tx.get("to") == st.session_state.current_user]
        
        if not user_transactions:
            st.info("No transactions found.")
        else:
            # Convert to DataFrame for better display
            tx_df = pd.DataFrame(user_transactions)
            tx_df["type"] = tx_df.apply(lambda x: "Sent" if x["from"] == st.session_state.current_user else "Received", axis=1)
            tx_df = tx_df[["id", "type", "amount", "coin", "timestamp"]]
            
            # Display transactions with color
            for idx, tx in tx_df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        st.write(tx["timestamp"])
                    with col2:
                        if tx["type"] == "Sent":
                            st.markdown(f"🔴 **Sent {tx['amount']} {tx['coin']}**")
                        else:
                            st.markdown(f"🟢 **Received {tx['amount']} {tx['coin']}**")
                    with col3:
                        st.code(tx["id"], language=None)
                st.divider()

    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.current_user = None
        st.rerun()

# Main app
def main():
    st.set_page_config(page_title="Crypto Payment System", page_icon="💰", layout="wide")
    
    # Add custom styling
    st.markdown("""
    <style>
    .stButton button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
    }
    div.stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    div.stTabs [data-baseweb="tab"] {
        border-radius: 5px 5px 0px 0px;
        padding: 10px 20px;
        background-color: #f0f2f6;
    }
    div.stTabs [aria-selected="true"] {
        background-color: #4e8cff;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Check for files and initialize if they don't exist
    initialize_app()
    
    # Render appropriate page based on authentication state
    if st.session_state.authenticated:
        dashboard()
    else:
        login_page()

if __name__ == "__main__":
    main()
