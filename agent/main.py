"""Entry point of the Vaani agent. The talking pipe is added in Phase 1, step 3."""

from settings import load_settings


def main() -> None:
    settings = load_settings()
    count = len(settings.public())
    print(f"Vaani agent: settings loaded ({count} public settings). No pipeline yet.")


if __name__ == "__main__":
    main()
