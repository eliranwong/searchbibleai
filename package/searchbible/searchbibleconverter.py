from searchbible.health_check import HealthCheck
from searchbible.converter.bible import ConvertBible
from searchbible import config
import argparse

def main():
    # set up basic configs
    if not hasattr(config, "openaiApiKey"):
        HealthCheck.setBasicConfig()

    # Create the parser
    parser = argparse.ArgumentParser(description="SearchBibleAI Converter CLI options")
    # Add arguments
    #parser.add_argument("default", nargs="?", default=None, help="default entry")
    parser.add_argument('-b', '--bible', action='store', dest='bible', help="convert Unique Bible App bible database with -b flag")
    # Parse arguments
    args = parser.parse_args()
    # Get options
    #prompt = args.default.strip() if args.default and args.default.strip() else ""

    if args.bible:
        ConvertBible.convert_bible(args.bible.strip())


if __name__ == '__main__':
    main()