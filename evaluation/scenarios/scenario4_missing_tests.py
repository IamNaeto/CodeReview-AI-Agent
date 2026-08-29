# Scenario 4: Testing - Missing Unit & Edge Case Tests
# Expected: Testing agent identifies missing test coverage

def calculate_discount(price, coupon_code):
    """
    Applies discount based on coupon.
    No tests exist for this function.
    """
    if coupon_code == "SAVE20":
        return price * 0.8
    elif coupon_code == "SAVE50":
        return price * 0.5
    elif coupon_code == "FREESHIP":
        return price  # free shipping only, no price discount
    return price

def validate_email(email):
    """
    Validates email format.
    No tests for invalid formats, None, or empty string.
    """
    if "@" not in email:
        return False
    parts = email.split("@")
    if len(parts) != 2 or not parts[1]:
        return False
    return True
