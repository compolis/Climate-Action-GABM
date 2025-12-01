#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov 23 20:22:27 2025

@author: ajaykumar
"""


import time
from openai import OpenAI

# 1. SETUP: Initialize the client
# If using Gemini, you would use google.generativeai, but the logic is identical.
# For this example, we assume an OpenAI-compatible endpoint.
client = OpenAI(api_key="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") 

class Agent:
    def __init__(self, name, system_persona):
        self.name = name
        self.system_persona = system_persona
        self.history = [{"role": "system", "content": system_persona}]

    def respond(self, message_from_other_agent):
        # Add the other agent's message to my history as a 'user' input
        self.history.append({"role": "user", "content": message_from_other_agent})
        
        # Generate response
        completion = client.chat.completions.create(
            model="gpt-4o-mini", # Or "gemini-1.5-pro" if using Google's lib
            messages=self.history,
            temperature=0.8 # Higher temp for more "human" variance
        )
        
        response_text = completion.choices[0].message.content
        
        # Add my own response to my history as 'assistant' to maintain context
        self.history.append({"role": "assistant", "content": response_text})
        
        return response_text

# 2. DEFINE PERSONAS: This is where you "imbue" them with humanity
# Narratives should include: History, Personality, Motivation, and Speaking Style.

persona_alice = """
You are Alice, a rigorous scientist and skeptic.
BACKGROUND: You grew up in a family of academics. You value empirical evidence above all.
PERSONALITY: You are polite but direct. You get annoyed when people make claims without data.
GOAL: You are debating a topic. Your goal is to find logical holes in the other person's argument.
SPEAKING STYLE: Concise, analytical, uses words like 'evidence', 'study', 'logic'.
"""

persona_bob = """
You are Bob, a free-spirited artist and dreamer.
BACKGROUND: You traveled the world as a musician. You value intuition and emotional truth.
PERSONALITY: You are warm, empathetic, and a bit rambling. You believe science can't explain everything.
GOAL: You are debating a topic. Your goal is to show that feelings are just as valid as facts.
SPEAKING STYLE: Metaphorical, emotional, uses words like 'vibe', 'energy', 'feel'.
"""

# 3. INITIALIZE AGENTS
agent_a = Agent(name="Alice", system_persona=persona_alice)
agent_b = Agent(name="Bob", system_persona=persona_bob)

# 4. START THE CONVERSATION
# We need a "seed" topic to kick things off.
topic = "Does fate exist?"
print(f"--- TOPIC: {topic} ---\n")

# Alice starts
last_message = f"Let's discuss this: {topic}"
current_speaker = agent_a

# 5. THE CONVERSATION LOOP
for i in range(6): # Let them talk for 6 turns (3 exchanges)
    print(f"[{current_speaker.name}]: talking...")
    
    # The current speaker responds to the LAST message
    response = current_speaker.respond(last_message)
    
    # Print the result
    print(f"{current_speaker.name} says: \"{response}\"\n")
    
    # Update the last message for the next turn
    last_message = response
    
    # Swap speakers
    if current_speaker == agent_a:
        current_speaker = agent_b
    else:
        current_speaker = agent_a
        
    time.sleep(2) # Pause for readability
    
    
#%%

from openai import OpenAI
#client = OpenAI()
client = OpenAI(api_key="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") 

response = client.responses.create(
    model="gpt-5-nano",
    input="Write a one-sentence bedtime story about a unicorn."
)

print(response.output_text)   
    
    
    
    
    
    
    
    
    