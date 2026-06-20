import sys
import argparse
from datetime import datetime, date, timedelta
from licensing import generate_activation_key, verify_license_key

def main():
    parser = argparse.ArgumentParser(description="pdf2tally License Key Generator")
    parser.add_argument("-s", "--signature", required=True, help="Machine signature (e.g. ABCD-EF01-2345-6789)")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-l", "--lifetime", action="store_true", help="Generate a lifetime key")
    group.add_argument("-m", "--months", type=int, help="Number of months of validity")
    group.add_argument("-d", "--days", type=int, help="Number of days of validity")
    group.add_argument("-e", "--expiry", help="Exact expiry date in YYYYMMDD format")

    args = parser.parse_args()

    signature = args.signature.strip().upper()
    
    if args.lifetime:
        expiry_str = "99991231"
        desc = "Lifetime"
    elif args.months:
        # Standard monthly calculation: 30 days per month
        expiry_date = date.today() + timedelta(days=30 * args.months)
        expiry_str = expiry_date.strftime("%Y%m%d")
        desc = f"{args.months} Month(s) (Expires {expiry_date.strftime('%d-%b-%Y')})"
    elif args.days:
        expiry_date = date.today() + timedelta(days=args.days)
        expiry_str = expiry_date.strftime("%Y%m%d")
        desc = f"{args.days} Day(s) (Expires {expiry_date.strftime('%d-%b-%Y')})"
    elif args.expiry:
        try:
            expiry_date = datetime.strptime(args.expiry, "%Y%m%d").date()
            expiry_str = args.expiry
            desc = f"Custom Expiry (Expires {expiry_date.strftime('%d-%b-%Y')})"
        except ValueError:
            print("Error: Expiry date must be in YYYYMMDD format.")
            sys.exit(1)
            
    key = generate_activation_key(signature, expiry_str)
    
    print("\n" + "="*50)
    print("         pdf2tally LICENSE KEY GENERATOR")
    print("="*50)
    print(f"Machine Signature : {signature}")
    print(f"License Duration  : {desc}")
    print(f"Activation Key    : {key}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
