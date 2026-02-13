# Roadmap

## Table of Contents
1. [Overview](#overview)
2. [1.0](#10)
3. [0.2](#02)


## Overview
This file outlines planned next steps and future goals.


## 1.0
- Criteria and features to be determined...


## 0.2
- Add src/cag directory
  - src/cag/agent.py
  - src/cag/model.py
  - src/cag/__init__.py
  - src/cag/__main__.py
- agent.py  
  - Agents will:
    - Belong to "networks" of other Agents
    - Be able to use LLM API prompts and responses to have a "conversations" with other agents.
    - Modify their opinions based on their biases and what they "learn" or are influenced by in the conversation with other agents.
- model.py
  - 10 majority agents will be initialised with personas from the survey
  - 1 minority agent will be initialised from each extremity
  - Agents will interact with other agents a set number of times
  - All prompts/responses will be cached.
  - Graphs will be output to show how individual and aggregate opinions change over time.