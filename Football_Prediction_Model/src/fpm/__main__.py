"""CLI: python -m fpm {ingest|load|backtest|selftest}"""
import sys


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "ingest":
        from . import ingest
        print(f"Seasons on disk: {', '.join(ingest.download_all())}")
    elif cmd == "load":
        from . import load
        print(f"Total matches loaded: {load.load_all()}")
    elif cmd == "backtest":
        from . import backtest
        print(f"Report written to {backtest.run()}")
    elif cmd == "selftest":
        from . import selftest
        selftest.run()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
