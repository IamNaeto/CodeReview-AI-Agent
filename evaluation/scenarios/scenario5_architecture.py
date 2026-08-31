# Scenario 5: Architecture - God Class & Tight Coupling
# Expected: Architecture and Quality findings

class OrderManager:
    """
    God Class: handles order logic, payments, notifications,
    inventory, and reporting all in one class.
    """

    def __init__(self):
        self.db = DatabaseConnection()
        self.payment_gateway = StripeAPI()
        self.email_service = SendGridAPI()
        self.inventory_service = InventoryAPI()
        self.reporting_service = ReportingAPI()

    def create_order(self, user_id, items):
        # Business logic mixed with data access, external calls, and notifications
        total = 0
        for item in items:
            price = self.db.query("SELECT price FROM products WHERE id = ?", (item['id'],))[0]
            total += price * item['qty']
            self.inventory_service.deduct(item['id'], item['qty'])

        order_id = self.db.insert("INSERT INTO orders (user_id, total) VALUES (?, ?)", (user_id, total))

        self.payment_gateway.charge(user_id, total)
        self.email_service.send(user_id, "Order confirmed", f"Order {order_id} created")
        self.reporting_service.track("order_created", {"order_id": order_id, "total": total})

        return order_id

    def generate_monthly_report(self, month):
        # Reporting logic mixed into order manager
        orders = self.db.query("SELECT * FROM orders WHERE created_at LIKE ?", (f"{month}%",))
        report = []
        for order in orders:
            user = self.db.query("SELECT * FROM users WHERE id = ?", (order['user_id'],))[0]
            report.append({**order, "user_email": user['email']})
        return report

