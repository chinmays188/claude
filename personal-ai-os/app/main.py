import sys

from app.agents.orchestrator import Orchestrator
from app.providers.gemini_provider import GeminiProvider


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python -m app.main "<your message>"')
        sys.exit(1)

    text = " ".join(sys.argv[1:])
    orchestrator = Orchestrator(llm=GeminiProvider())
    result = orchestrator.handle(text)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
