
class BasicRegularAgent:
    def __init__(self):
        self.history = []

    def receive_message(self, message):
        # Basic message handling logic
        print(f"Received message: {message}")
        self.update_history(message)

    def get_opinion(self):
        # Basic opinion logic
        return "C"

    def update_history(self, message):
        # Basic history update logic
        self.history.append(message)
