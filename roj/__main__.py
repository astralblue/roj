import logging
import sys

import roj


def main():
    logging.basicConfig(level=logging.INFO)
    sys.exit(roj.RunOnJail().main())


if __name__ == "__main__":
    main()
