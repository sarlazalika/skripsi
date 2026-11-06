import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

def perform_apriori(df, min_support=0.005, min_threshold=0.5, return_stats=False):
    if df.empty:
        if return_stats:
            return None, None, {'n_transactions': 0, 'n_products': 0, 'n_itemsets': 0, 'n_rules': 0}
        return None, None
    
    # 1. Transform data into transactional format (One-Hot Encoded)
    # Group by id_transaksi and aggregate products into a binary matrix
    basket = (df.groupby(['id_transaksi', 'produk'])['jumlah']
              .sum().unstack().fillna(0) > 0)
    
    n_transactions = len(basket)
    n_products = len(basket.columns)
    
    # 2. Apply Apriori algorithm
    frequent_itemsets = apriori(basket, min_support=min_support, use_colnames=True)
    
    if frequent_itemsets.empty:
        stats = {
            'n_transactions': n_transactions,
            'n_products': n_products,
            'n_itemsets': 0,
            'n_rules': 0
        }
        if return_stats:
            return None, None, stats
        return None, None

    # 3. Generate Association Rules
    rules = association_rules(frequent_itemsets, metric="confidence", min_threshold=min_threshold)
    
    stats = {
        'n_transactions': n_transactions,
        'n_products': n_products,
        'n_itemsets': len(frequent_itemsets),
        'n_rules': len(rules) if rules is not None else 0
    }
    
    if return_stats:
        return frequent_itemsets, rules, stats
    return frequent_itemsets, rules
