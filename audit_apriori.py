import sqlite3
import pandas as pd
from analysis.apriori import perform_apriori

def run_audit():
    conn = sqlite3.connect('database.db')
    
    # Get active session
    session = pd.read_sql_query("SELECT id FROM upload_session WHERE status='cleaned' ORDER BY id DESC LIMIT 1", conn)
    if session.empty:
        print("No active session")
        return
    session_id = session.iloc[0]['id']
    
    df = pd.read_sql_query('SELECT id_transaksi, produk, jumlah FROM cleaned_transaksi WHERE session_id=?', conn, params=(session_id,))
    conn.close()
    
    print(f"Data rows fetched: {len(df)}")
    
    frequent_itemsets, rules = perform_apriori(df, min_support=0.01, min_threshold=0.1)
    
    if frequent_itemsets is not None:
        print(f"Frequent itemsets count: {len(frequent_itemsets)}")
    else:
        print("No frequent itemsets")
        
    if rules is not None:
        print(f"Rules count: {len(rules)}")
        print("\nColumns in rules:")
        print(rules.columns.tolist())
        print("\nSample rule:")
        if len(rules) > 0:
            sample = rules.iloc[0]
            print(f"Antecedents: {list(sample['antecedents'])}")
            print(f"Consequents: {list(sample['consequents'])}")
            print(f"Support: {sample['support']}")
            print(f"Confidence: {sample['confidence']}")
            print(f"Lift: {sample['lift']}")
    else:
        print("No rules")

if __name__ == "__main__":
    run_audit()
