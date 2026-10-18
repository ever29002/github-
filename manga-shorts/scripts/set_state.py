"""Move a job to a new state, e.g. after a human gate or a QC result.

Usage: python3 scripts/set_state.py <job> <state> [--note TEXT]
"""

import argparse

from common import STATES, job_dir, load_status, set_state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job")
    parser.add_argument("state", nargs="?", choices=STATES)
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    path = job_dir(args.job)
    if args.state:
        set_state(path, args.state, args.note)
    print(load_status(path)["state"])


if __name__ == "__main__":
    main()
