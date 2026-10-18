import argparse
from pathlib import Path

from scripts.grounding import ground_topic
from scripts.sources import format_citation
from scripts.workspace import resolve_workspace


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace")
    parser.add_argument("subject")
    parser.add_argument("topic")
    parser.add_argument("grade")
    parser.add_argument("--general", action="store_true")
    parser.add_argument("--photo")
    args = parser.parse_args()

    workspace = resolve_workspace(Path(args.workspace))
    result = ground_topic(
        workspace, args.subject, args.topic, args.grade,
        is_curricular=not args.general,
        santillana_photo_path=Path(args.photo) if args.photo else None,
    )

    if result["gap"] is not None:
        print(f"gap: {result['gap']}")
    for source in result["sources"]:
        print(format_citation(source))


if __name__ == "__main__":
    main()
