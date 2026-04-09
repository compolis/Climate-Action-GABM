"""Quick test: load one row of survey data, build an agent, print persona and narrative."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cag.__main__ import main

# Just run main() — it already loads data, creates agents, and prints 20 personas.
# We're piggybacking on that to eyeball the output.
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(message)s", handlers=[logging.StreamHandler(sys.stdout)])
    main()
