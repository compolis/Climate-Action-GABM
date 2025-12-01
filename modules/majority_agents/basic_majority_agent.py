



class BasicMajorityAgent:
    def __init__(self, name):
        self.name = name
        self.history = []

    def receive_message(self, message):
        # Basic message handling logic
        print(f"{self.name} received message: {message}")
        update_history(message)


    def get_opinion(self):
        # Basic opinion logic
        return "C"

    def update_history(self, message):
        # Basic history update logic
        self.history.append(message)

