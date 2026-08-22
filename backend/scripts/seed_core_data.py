import sys
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Ensure the backend directory is in the import path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database.session import SessionLocal
from app.database.models.enums import MerchantStatus, RiskProfile, TransactionStatus
from app.database.models import Merchant, Customer, Device, Transaction

def seed_data():
    db = SessionLocal()
    try:
        print("Starting core data seeding...")

        # 1. Seed exactly 3 Merchants
        merchants_data = [
            {"name": "VeloCart Electronics", "slug": "velocart-electronics", "status": MerchantStatus.ACTIVE},
            {"name": "ScribeFlow Premium", "slug": "scribeflow-premium", "status": MerchantStatus.ACTIVE},
            {"name": "NovaPixel Assets", "slug": "novapixel-assets", "status": MerchantStatus.ACTIVE},
        ]

        merchants = {}
        for m_info in merchants_data:
            existing = db.query(Merchant).filter(Merchant.slug == m_info["slug"]).first()
            if not existing:
                merchant = Merchant(name=m_info["name"], slug=m_info["slug"], status=m_info["status"])
                db.add(merchant)
                db.flush()  # populate ID
                merchants[merchant.slug] = merchant
                print(f"Created merchant: {merchant.name}")
            else:
                merchants[existing.slug] = existing
                print(f"Merchant already exists: {existing.name}")

        # 2. Seed at least 12 Customers (4 per merchant)
        customers_data = [
            # VeloCart Customers
            {"m_slug": "velocart-electronics", "ext_id": "cust_vc_001", "email": "aarav.sharma@gmail.com", "name": "Aarav Sharma", "risk": RiskProfile.LOW, "age_days": 180},
            {"m_slug": "velocart-electronics", "ext_id": "cust_vc_002", "email": "diya.patel@gmail.com", "name": "Diya Patel", "risk": RiskProfile.LOW, "age_days": 90},
            {"m_slug": "velocart-electronics", "ext_id": "cust_vc_003", "email": "kabir.singh@yahoo.com", "name": "Kabir Singh", "risk": RiskProfile.MEDIUM, "age_days": 15},
            {"m_slug": "velocart-electronics", "ext_id": "cust_vc_004", "email": "isha.gupta@outlook.com", "name": "Isha Gupta", "risk": RiskProfile.HIGH, "age_days": 2},
            
            # ScribeFlow Customers
            {"m_slug": "scribeflow-premium", "ext_id": "cust_sf_001", "email": "rohan.das@gmail.com", "name": "Rohan Das", "risk": RiskProfile.LOW, "age_days": 365},
            {"m_slug": "scribeflow-premium", "ext_id": "cust_sf_002", "email": "ananya.sen@gmail.com", "name": "Ananya Sen", "risk": RiskProfile.LOW, "age_days": 120},
            {"m_slug": "scribeflow-premium", "ext_id": "cust_sf_003", "email": "dev.malhotra@hotmail.com", "name": "Dev Malhotra", "risk": RiskProfile.MEDIUM, "age_days": 40},
            {"m_slug": "scribeflow-premium", "ext_id": "cust_sf_004", "email": "ria.verma@gmail.com", "name": "Ria Verma", "risk": RiskProfile.HIGH, "age_days": 5},
            
            # NovaPixel Customers
            {"m_slug": "novapixel-assets", "ext_id": "cust_np_001", "email": "vikram.rao@gmail.com", "name": "Vikram Rao", "risk": RiskProfile.LOW, "age_days": 240},
            {"m_slug": "novapixel-assets", "ext_id": "cust_np_002", "email": "meera.nair@gmail.com", "name": "Meera Nair", "risk": RiskProfile.LOW, "age_days": 150},
            {"m_slug": "novapixel-assets", "ext_id": "cust_np_003", "email": "aditya.roy@yahoo.com", "name": "Aditya Roy", "risk": RiskProfile.MEDIUM, "age_days": 30},
            {"m_slug": "novapixel-assets", "ext_id": "cust_np_004", "email": "zara.khan@gmail.com", "name": "Zara Khan", "risk": RiskProfile.HIGH, "age_days": 1},
        ]

        customers = {}
        for c_info in customers_data:
            m = merchants[c_info["m_slug"]]
            existing = db.query(Customer).filter(
                Customer.merchant_id == m.id,
                Customer.external_customer_id == c_info["ext_id"]
            ).first()
            if not existing:
                ac_created = datetime.now(timezone.utc) - timedelta(days=c_info["age_days"])
                customer = Customer(
                    merchant_id=m.id,
                    external_customer_id=c_info["ext_id"],
                    email=c_info["email"],
                    full_name=c_info["name"],
                    account_created_at=ac_created,
                    risk_profile=c_info["risk"]
                )
                db.add(customer)
                db.flush()
                customers[c_info["ext_id"]] = customer
                print(f"Created customer: {customer.full_name} for merchant {m.name}")
            else:
                customers[c_info["ext_id"]] = existing
                print(f"Customer already exists: {existing.full_name}")

        # 3. Seed at least 15 Devices (spread over customers)
        devices_data = [
            # Aarav Sharma - VeloCart (2 devices: trusted phone, trusted laptop)
            {"c_ext_id": "cust_vc_001", "fp": "dev_fp_vc_001_phone", "type": "Mobile (iOS)", "trusted": True, "age_days": 170},
            {"c_ext_id": "cust_vc_001", "fp": "dev_fp_vc_001_laptop", "type": "Desktop (macOS)", "trusted": True, "age_days": 120},
            
            # Diya Patel - VeloCart (1 trusted laptop)
            {"c_ext_id": "cust_vc_002", "fp": "dev_fp_vc_002_laptop", "type": "Desktop (Windows)", "trusted": True, "age_days": 85},
            
            # Kabir Singh - VeloCart (2 devices: trusted mobile, untrusted desktop)
            {"c_ext_id": "cust_vc_003", "fp": "dev_fp_vc_003_mobile", "type": "Mobile (Android)", "trusted": True, "age_days": 14},
            {"c_ext_id": "cust_vc_003", "fp": "dev_fp_vc_003_desktop", "type": "Desktop (Linux)", "trusted": False, "age_days": 2},
            
            # Isha Gupta - VeloCart (1 untrusted mobile)
            {"c_ext_id": "cust_vc_004", "fp": "dev_fp_vc_004_mobile", "type": "Mobile (Android)", "trusted": False, "age_days": 1},
            
            # Rohan Das - ScribeFlow (1 trusted laptop)
            {"c_ext_id": "cust_sf_001", "fp": "dev_fp_sf_001_laptop", "type": "Desktop (macOS)", "trusted": True, "age_days": 350},
            
            # Ananya Sen - ScribeFlow (2 trusted devices)
            {"c_ext_id": "cust_sf_002", "fp": "dev_fp_sf_002_phone", "type": "Mobile (iOS)", "trusted": True, "age_days": 115},
            {"c_ext_id": "cust_sf_002", "fp": "dev_fp_sf_002_tablet", "type": "Tablet (iOS)", "trusted": True, "age_days": 80},
            
            # Dev Malhotra - ScribeFlow (2 devices: trusted, untrusted)
            {"c_ext_id": "cust_sf_003", "fp": "dev_fp_sf_003_laptop", "type": "Desktop (Windows)", "trusted": True, "age_days": 38},
            {"c_ext_id": "cust_sf_003", "fp": "dev_fp_sf_003_cyber", "type": "Desktop (Unknown)", "trusted": False, "age_days": 1},
            
            # Ria Verma - ScribeFlow (1 untrusted mobile)
            {"c_ext_id": "cust_sf_004", "fp": "dev_fp_sf_004_phone", "type": "Mobile (Android)", "trusted": False, "age_days": 4},
            
            # Vikram Rao - NovaPixel (1 trusted laptop)
            {"c_ext_id": "cust_np_001", "fp": "dev_fp_np_001_laptop", "type": "Desktop (Windows)", "trusted": True, "age_days": 230},
            
            # Meera Nair - NovaPixel (1 trusted phone)
            {"c_ext_id": "cust_np_002", "fp": "dev_fp_np_002_phone", "type": "Mobile (iOS)", "trusted": True, "age_days": 140},
            
            # Aditya Roy - NovaPixel (1 trusted laptop)
            {"c_ext_id": "cust_np_003", "fp": "dev_fp_np_003_laptop", "type": "Desktop (macOS)", "trusted": True, "age_days": 28},
            
            # Zara Khan - NovaPixel (1 untrusted mobile)
            {"c_ext_id": "cust_np_004", "fp": "dev_fp_np_004_phone", "type": "Mobile (Android)", "trusted": False, "age_days": 1},
        ]

        devices = {}
        for d_info in devices_data:
            c = customers[d_info["c_ext_id"]]
            existing = db.query(Device).filter(
                Device.customer_id == c.id,
                Device.device_fingerprint == d_info["fp"]
            ).first()
            if not existing:
                seen_at = datetime.now(timezone.utc) - timedelta(days=d_info["age_days"])
                device = Device(
                    customer_id=c.id,
                    device_fingerprint=d_info["fp"],
                    device_type=d_info["type"],
                    is_trusted=d_info["trusted"],
                    first_seen_at=seen_at,
                    last_seen_at=datetime.now(timezone.utc)
                )
                db.add(device)
                db.flush()
                devices[d_info["fp"]] = device
                print(f"Created device: {device.device_fingerprint} for {c.full_name}")
            else:
                devices[d_info["fp"]] = existing
                print(f"Device already exists: {existing.device_fingerprint}")

        # 4. Seed at least 30 Transactions
        transactions_data = [
            # Aarav Sharma - VeloCart
            {"tx_id": "tx_vc_101", "c_id": "cust_vc_001", "m_slug": "velocart-electronics", "dev_fp": "dev_fp_vc_001_phone", "amount": 25000.00, "pm": "UPI", "loc": "Mumbai, India", "status": TransactionStatus.SUCCESS, "hours_ago": 720},
            {"tx_id": "tx_vc_102", "c_id": "cust_vc_001", "m_slug": "velocart-electronics", "dev_fp": "dev_fp_vc_001_laptop", "amount": 89000.00, "pm": "NetBanking", "loc": "Mumbai, India", "status": TransactionStatus.SUCCESS, "hours_ago": 480},
            {"tx_id": "tx_vc_103", "c_id": "cust_vc_001", "m_slug": "velocart-electronics", "dev_fp": "dev_fp_vc_001_phone", "amount": 12000.00, "pm": "UPI", "loc": "Mumbai, India", "status": TransactionStatus.SUCCESS, "hours_ago": 12},
            
            # Diya Patel - VeloCart
            {"tx_id": "tx_vc_201", "c_id": "cust_vc_002", "m_slug": "velocart-electronics", "dev_fp": "dev_fp_vc_002_laptop", "amount": 45000.00, "pm": "Credit Card", "loc": "Bangalore, India", "status": TransactionStatus.SUCCESS, "hours_ago": 2000},
            {"tx_id": "tx_vc_202", "c_id": "cust_vc_002", "m_slug": "velocart-electronics", "dev_fp": "dev_fp_vc_002_laptop", "amount": 3200.00, "pm": "Credit Card", "loc": "Bangalore, India", "status": TransactionStatus.SUCCESS, "hours_ago": 120},
            
            # Kabir Singh - VeloCart
            {"tx_id": "tx_vc_301", "c_id": "cust_vc_003", "m_slug": "velocart-electronics", "dev_fp": "dev_fp_vc_003_mobile", "amount": 15000.00, "pm": "UPI", "loc": "Delhi, India", "status": TransactionStatus.SUCCESS, "hours_ago": 240},
            {"tx_id": "tx_vc_302", "c_id": "cust_vc_003", "m_slug": "velocart-electronics", "dev_fp": "dev_fp_vc_003_desktop", "amount": 95000.00, "pm": "Credit Card", "loc": "Delhi, India", "status": TransactionStatus.FAILED, "hours_ago": 48},
            {"tx_id": "tx_vc_303", "c_id": "cust_vc_003", "m_slug": "velocart-electronics", "dev_fp": "dev_fp_vc_003_desktop", "amount": 95000.00, "pm": "Credit Card", "loc": "Delhi, India", "status": TransactionStatus.SUCCESS, "hours_ago": 47},
            {"tx_id": "tx_vc_304", "c_id": "cust_vc_003", "m_slug": "velocart-electronics", "dev_fp": "dev_fp_vc_003_desktop", "amount": 120000.00, "pm": "Credit Card", "loc": "Moscow, Russia", "status": TransactionStatus.PENDING, "hours_ago": 1}, # SUSPICIOUS
            
            # Isha Gupta - VeloCart
            {"tx_id": "tx_vc_401", "c_id": "cust_vc_004", "m_slug": "velocart-electronics", "dev_fp": "dev_fp_vc_004_mobile", "amount": 55000.00, "pm": "Credit Card", "loc": "Lagos, Nigeria", "status": TransactionStatus.BLOCKED, "hours_ago": 24}, # BLOCKED
            {"tx_id": "tx_vc_402", "c_id": "cust_vc_004", "m_slug": "velocart-electronics", "dev_fp": "dev_fp_vc_004_mobile", "amount": 500.00, "pm": "Credit Card", "loc": "Delhi, India", "status": TransactionStatus.SUCCESS, "hours_ago": 2},
            
            # Rohan Das - ScribeFlow
            {"tx_id": "tx_sf_101", "c_id": "cust_sf_001", "m_slug": "scribeflow-premium", "dev_fp": "dev_fp_sf_001_laptop", "amount": 999.00, "pm": "UPI", "loc": "Kolkata, India", "status": TransactionStatus.SUCCESS, "hours_ago": 8000},
            {"tx_id": "tx_sf_102", "c_id": "cust_sf_001", "m_slug": "scribeflow-premium", "dev_fp": "dev_fp_sf_001_laptop", "amount": 999.00, "pm": "UPI", "loc": "Kolkata, India", "status": TransactionStatus.SUCCESS, "hours_ago": 7280},
            {"tx_id": "tx_sf_103", "c_id": "cust_sf_001", "m_slug": "scribeflow-premium", "dev_fp": "dev_fp_sf_001_laptop", "amount": 999.00, "pm": "UPI", "loc": "Kolkata, India", "status": TransactionStatus.SUCCESS, "hours_ago": 6560},
            {"tx_id": "tx_sf_104", "c_id": "cust_sf_001", "m_slug": "scribeflow-premium", "dev_fp": "dev_fp_sf_001_laptop", "amount": 12000.00, "pm": "Debit Card", "loc": "Kolkata, India", "status": TransactionStatus.SUCCESS, "hours_ago": 5},
            
            # Ananya Sen - ScribeFlow
            {"tx_id": "tx_sf_201", "c_id": "cust_sf_002", "m_slug": "scribeflow-premium", "dev_fp": "dev_fp_sf_002_phone", "amount": 499.00, "pm": "Credit Card", "loc": "Pune, India", "status": TransactionStatus.SUCCESS, "hours_ago": 2800},
            {"tx_id": "tx_sf_202", "c_id": "cust_sf_002", "m_slug": "scribeflow-premium", "dev_fp": "dev_fp_sf_002_tablet", "amount": 999.00, "pm": "Credit Card", "loc": "Pune, India", "status": TransactionStatus.SUCCESS, "hours_ago": 1400},
            
            # Dev Malhotra - ScribeFlow
            {"tx_id": "tx_sf_301", "c_id": "cust_sf_003", "m_slug": "scribeflow-premium", "dev_fp": "dev_fp_sf_003_laptop", "amount": 999.00, "pm": "NetBanking", "loc": "Hyderabad, India", "status": TransactionStatus.SUCCESS, "hours_ago": 720},
            {"tx_id": "tx_sf_302", "c_id": "cust_sf_003", "m_slug": "scribeflow-premium", "dev_fp": "dev_fp_sf_003_cyber", "amount": 45000.00, "pm": "Credit Card", "loc": "London, UK", "status": TransactionStatus.SUCCESS, "hours_ago": 24}, # SUSPICIOUS
            
            # Ria Verma - ScribeFlow
            {"tx_id": "tx_sf_401", "c_id": "cust_sf_004", "m_slug": "scribeflow-premium", "dev_fp": "dev_fp_sf_004_phone", "amount": 999.00, "pm": "Debit Card", "loc": "Noida, India", "status": TransactionStatus.SUCCESS, "hours_ago": 96},
            {"tx_id": "tx_sf_402", "c_id": "cust_sf_004", "m_slug": "scribeflow-premium", "dev_fp": "dev_fp_sf_004_phone", "amount": 999.00, "pm": "Debit Card", "loc": "Noida, India", "status": TransactionStatus.FAILED, "hours_ago": 12},
            
            # Vikram Rao - NovaPixel
            {"tx_id": "tx_np_101", "c_id": "cust_np_001", "m_slug": "novapixel-assets", "dev_fp": "dev_fp_np_001_laptop", "amount": 5000.00, "pm": "UPI", "loc": "Chennai, India", "status": TransactionStatus.SUCCESS, "hours_ago": 5700},
            {"tx_id": "tx_np_102", "c_id": "cust_np_001", "m_slug": "novapixel-assets", "dev_fp": "dev_fp_np_001_laptop", "amount": 12000.00, "pm": "UPI", "loc": "Chennai, India", "status": TransactionStatus.SUCCESS, "hours_ago": 2400},
            {"tx_id": "tx_np_103", "c_id": "cust_np_001", "m_slug": "novapixel-assets", "dev_fp": "dev_fp_np_001_laptop", "amount": 3500.00, "pm": "UPI", "loc": "Chennai, India", "status": TransactionStatus.SUCCESS, "hours_ago": 48},
            
            # Meera Nair - NovaPixel
            {"tx_id": "tx_np_201", "c_id": "cust_np_002", "m_slug": "novapixel-assets", "dev_fp": "dev_fp_np_002_phone", "amount": 1500.00, "pm": "Debit Card", "loc": "Kochi, India", "status": TransactionStatus.SUCCESS, "hours_ago": 3300},
            {"tx_id": "tx_np_202", "c_id": "cust_np_002", "m_slug": "novapixel-assets", "dev_fp": "dev_fp_np_002_phone", "amount": 7500.00, "pm": "Debit Card", "loc": "Kochi, India", "status": TransactionStatus.SUCCESS, "hours_ago": 1500},
            
            # Aditya Roy - NovaPixel
            {"tx_id": "tx_np_301", "c_id": "cust_np_003", "m_slug": "novapixel-assets", "dev_fp": "dev_fp_np_003_laptop", "amount": 25000.00, "pm": "NetBanking", "loc": "Ahmedabad, India", "status": TransactionStatus.SUCCESS, "hours_ago": 600},
            
            # Zara Khan - NovaPixel
            {"tx_id": "tx_np_401", "c_id": "cust_np_004", "m_slug": "novapixel-assets", "dev_fp": "dev_fp_np_004_phone", "amount": 3000.00, "pm": "Credit Card", "loc": "Jaipur, India", "status": TransactionStatus.SUCCESS, "hours_ago": 24},
            {"tx_id": "tx_np_402", "c_id": "cust_np_004", "m_slug": "novapixel-assets", "dev_fp": "dev_fp_np_004_phone", "amount": 22000.00, "pm": "Credit Card", "loc": "Jaipur, India", "status": TransactionStatus.FAILED, "hours_ago": 12},
            {"tx_id": "tx_np_403", "c_id": "cust_np_004", "m_slug": "novapixel-assets", "dev_fp": "dev_fp_np_004_phone", "amount": 22000.00, "pm": "Credit Card", "loc": "Jaipur, India", "status": TransactionStatus.SUCCESS, "hours_ago": 11},
            
            # Global Null Device Transactions
            {"tx_id": "tx_global_501", "c_id": "cust_vc_001", "m_slug": "velocart-electronics", "dev_fp": None, "amount": 10000.00, "pm": "NetBanking", "loc": "Mumbai, India", "status": TransactionStatus.SUCCESS, "hours_ago": 72},
            {"tx_id": "tx_global_502", "c_id": "cust_sf_002", "m_slug": "scribeflow-premium", "dev_fp": None, "amount": 999.00, "pm": "UPI", "loc": "Pune, India", "status": TransactionStatus.SUCCESS, "hours_ago": 360},
        ]

        for tx_info in transactions_data:
            existing = db.query(Transaction).filter(
                Transaction.external_transaction_id == tx_info["tx_id"]
            ).first()
            if not existing:
                m = merchants[tx_info["m_slug"]]
                c = customers[tx_info["c_id"]]
                d = devices[tx_info["dev_fp"]] if tx_info["dev_fp"] else None
                occurred = datetime.now(timezone.utc) - timedelta(hours=tx_info["hours_ago"])
                transaction = Transaction(
                    external_transaction_id=tx_info["tx_id"],
                    merchant_id=m.id,
                    customer_id=c.id,
                    device_id=d.id if d else None,
                    amount=Decimal(str(tx_info["amount"])),
                    currency=tx_info.get("currency", "INR"),
                    payment_method=tx_info["pm"],
                    location=tx_info["loc"],
                    status=tx_info["status"],
                    occurred_at=occurred
                )
                db.add(transaction)
                print(f"Created transaction: {transaction.external_transaction_id} for amount {transaction.amount}")
            else:
                print(f"Transaction already exists: {existing.external_transaction_id}")

        db.commit()
        print("Core database seeding complete successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
