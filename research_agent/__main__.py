"""python -m research_agent

Fetches official pages through the Composio SDK, then renders the brief
from the adjudicated findings. The fetch does not change a verdict by itself.
"""

from research_agent.build_site import main as build_site
from research_agent.fetch_docs import main as fetch_docs


def main() -> None:
    fetch_docs()
    build_site()


if __name__ == "__main__":
    main()
