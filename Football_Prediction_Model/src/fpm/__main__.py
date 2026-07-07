"""CLI: python -m fpm {ingest|load|backtest|fixtures <csv>|predict|coupon|selftest}

predict and coupon accept --gate-passed only after a REAL-data backtest report
has been reviewed and shows calibration + positive value performance.
"""
import sys


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    gate = "--gate-passed" in sys.argv
    if cmd == "ingest":
        from . import ingest
        print(f"Seasons on disk: {', '.join(ingest.download_all())}")
    elif cmd == "load":
        from . import load
        print(f"Total matches loaded: {load.load_all()}")
    elif cmd == "backtest":
        from . import backtest
        print(f"Report written to {backtest.run()}")
    elif cmd == "fixtures":
        from . import predict
        print(f"Scheduled fixtures added: {predict.load_fixtures_csv(sys.argv[2])}")
    elif cmd == "predict":
        from . import predict
        path = predict.run(gate_passed=gate)
        if path:
            print(f"Cards written to {path}")
    elif cmd == "coupon":
        from . import coupon
        path = coupon.build(gate_passed=gate)
        if path:
            print(f"Coupon written to {path}")
    elif cmd == "selftest":
        from . import selftest
        selftest.run()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
