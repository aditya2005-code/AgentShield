import sys
import os

# Ensure the backend directory is in the import path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database.session import SessionLocal
from app.database.models import Merchant, Customer, Device, Transaction

def verify_data():
    db = SessionLocal()
    try:
        print("Starting core database verification...")
        
        # 1. Row counts
        merchants_count = db.query(Merchant).count()
        customers_count = db.query(Customer).count()
        devices_count = db.query(Device).count()
        transactions_count = db.query(Transaction).count()

        print(f"Row Counts:")
        print(f"- Merchants: {merchants_count} (Expected: 3)")
        print(f"- Customers: {customers_count} (Expected: >= 12)")
        print(f"- Devices: {devices_count} (Expected: >= 15)")
        print(f"- Transactions: {transactions_count} (Expected: >= 30)")

        assert merchants_count == 3, f"Unexpected merchant count: {merchants_count}"
        assert customers_count >= 12, f"Unexpected customer count: {customers_count}"
        assert devices_count >= 15, f"Unexpected device count: {devices_count}"
        assert transactions_count >= 30, f"Unexpected transaction count: {transactions_count}"

        print("[OK] Row counts verified successfully.")

        # 2. Relationship verification
        print("\nVerifying relationships...")

        # Merchant -> Customer
        for m in db.query(Merchant).all():
            assert len(m.customers) > 0, f"Merchant {m.name} has 0 customers"
            print(f"- Merchant '{m.name}' has {len(m.customers)} customers (Verified).")

        # Customer -> Device & Customer -> Transaction
        for c in db.query(Customer).limit(5).all():
            assert c.merchant is not None, f"Customer {c.full_name} has no associated merchant"
            print(f"- Customer '{c.full_name}' belongs to Merchant '{c.merchant.name}' (Verified).")
            print(f"  - Devices: {len(c.devices)}")
            print(f"  - Transactions: {len(c.transactions)}")

        # Transaction -> Merchant & Device
        for tx in db.query(Transaction).limit(5).all():
            assert tx.merchant is not None, f"Transaction {tx.external_transaction_id} has no merchant"
            assert tx.customer is not None, f"Transaction {tx.external_transaction_id} has no customer"
            if tx.device_id:
                assert tx.device is not None, f"Transaction {tx.external_transaction_id} has device_id but device relation is null"
                print(f"- Transaction '{tx.external_transaction_id}' linked to Device '{tx.device.device_fingerprint}' (Verified).")
            else:
                print(f"- Transaction '{tx.external_transaction_id}' has no associated device fingerprint (Verified null).")

        print("[OK] Relationships verified successfully.")
        print("\nDatabase Integrity Verification: PASSED")
    except Exception as e:
        print(f"[ERROR] Verification failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    verify_data()
