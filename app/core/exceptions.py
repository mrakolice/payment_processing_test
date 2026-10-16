class PaymentException(Exception):
    def __init__(self, payment_id):
        self.payment_id = payment_id

    def __str__(self):
        return f'Error with processing payment with id: {self.payment_id}'
