

# Add ability to import from higher up the file tree
import sys
sys.path.append("..")

from regular_agents.basic_regular_agent import BasicRegularAgent

n_agents = 100
n_sims = 1

for n in range(n_sims):

    regular_agents = []

    for i in range(n_agents):
        agent = BasicRegularAgent()
        regular_agents.append(agent)

    for agent in regular_agents:
        print(agent)

        agent.receive_message("Hello from controller")      
