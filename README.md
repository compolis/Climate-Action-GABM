<!-- Badges -->
<p align="left">
  <a href="https://github.com/compolis/Climate-Action-GABM/blob/main/LICENSE" title="License">
    <img src="https://img.shields.io/github/license/compolis/Climate-Action-GABM" alt="License" />
  </a>
  <a href="https://www.python.org/downloads/release/python-31212/" title="Python Version">
    <img src="https://img.shields.io/badge/python-3.12%2B-blue.svg" alt="Python Version" />
  </a>
  <!--
  <a href="https://compolis.github.io/Climate-Action-GABM/" title="Documentation">
    <img src="https://img.shields.io/badge/docs-Sphinx-green" alt="Documentation" />
  </a>
  -->
</p>

# Climate-Action-GABM


## Table of Contents
- [Overview](#overview)
- [License](#license)
- [Roadmap](#roadmap)
- [Change Log](#change-log)
- [Development History](#development-history)
- [Acknowledgements](#acknowledgements)


## Overview
Climate-Action-GABM is based on [GABM](https://github.com/compolis/GABM/) - a generative agent-based modelling framework.

The framework is used herein to attempt to understand the dynamics of social tipping or polarization under the influence of competing persuasion from two competing committed minorities with opposing goals.

GABM provides a framework for using Large Language Model (LLM) models to develop agent-based models. Agents can be endowed with human-like personas and engage in natural-language conversations using LLM models. By storing prompts and responses, processing these and providing them as context in prompts it is possible to effectively debate and influence the beliefs/desires/stances of agents.

Changes in individual agents beliefs/desires/stances can cascade through their networks to shape collective attitudes.

The vision for a first model is of agents playing a coordination (social-tipping) game with persuasive communication, where each agent chooses one of two options (climate mitigation action, no climate mitigation action). One committed minority group representing climate action advocates (such as green political parties, campaign groups, climate movements, etc.) will always vote for a climate mitigation action. Another committed minority group representing climate inaction advocates (such as climate-denial/delay political parties and grassroots groups) will always vote for no climate mitigation action. A larger majority group will be persuadable either way.

The model is based on survey data. This is used to construct the majority agents.


## License
See [LICENSE](LICENSE).


## Roadmap
See [ROADMAP.md](ROADMAP.md) for planned next steps and future goals.


## Change Log
See [CHANGE_LOG.md](CHANGE_LOG.md) for details of each release.


## Development History
The collaborative development of GABM is captured in the [DEVELOPMENT_HISTORY.md](DEVELOPMENT_HISTORY.md).


## Acknowledgements
This project was developed with significant assistance from [GitHub Copilot](https://github.com/features/copilot) for code generation, refactoring, and documentation improvements.

We gratefully acknowledge support from the [University of Leeds](https://www.leeds.ac.uk/). Funding for this project comes from a UKRI Future Leaders Fellowship awarded to [Professor Viktoria Spaiser](https://essl.leeds.ac.uk/politics/staff/102/professor-viktoria-spaiser) (grant reference: [UKRI2043](https://gtr.ukri.org/projects?ref=UKRI2043)).
