# Scenario 3: Correctness - Race Condition & Exception Handling
# Expected: High severity correctness findings

import threading

balance = 0
lock = threading.Lock()

def unsafe_increment(amount):
    # RACE CONDITION: no lock acquired
    global balance
    current = balance
    # simulated delay
    import time
    time.sleep(0.001)
    balance = current + amount

def process_payment(user_id, amount):
    try:
        charge_card(user_id, amount)
        update_balance(amount)
    except Exception as e:
        # SWALLOWED EXCEPTION: no retry, no notification, no rollback
        print("Error occurred")
        pass  # silently fails

def divide_resources(total, workers):
    # EDGE CASE: no zero check
    return total / workers
