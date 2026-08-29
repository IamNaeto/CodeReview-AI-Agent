# Scenario 2: Performance - N+1 Query & Inefficient Algorithm
# Expected: High severity performance findings

from database import db

def get_orders_with_items(customer_id):
    orders = db.query("SELECT * FROM orders WHERE customer_id = ?", (customer_id,))
    result = []
    for order in orders:
        # N+1 QUERY: fetching items individually in a loop
        items = db.query("SELECT * FROM order_items WHERE order_id = ?", (order['id'],))
        order['items'] = items
        result.append(order)
    return result

def find_duplicates(data):
    # O(n^2) algorithm where O(n) with set would suffice
    duplicates = []
    for i in range(len(data)):
        for j in range(i + 1, len(data)):
            if data[i] == data[j] and data[i] not in duplicates:
                duplicates.append(data[i])
    return duplicates
