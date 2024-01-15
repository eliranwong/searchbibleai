from searchbible.health_check import HealthCheck
from searchbible.converter.bible import ConvertBible
from searchbible import config
import argparse, os

def main():
    # set up basic configs
    if not hasattr(config, "openaiApiKey"):
        HealthCheck.setBasicConfig()

    # Create the parser
    parser = argparse.ArgumentParser(description="SearchBibleAI Converter CLI options")
    # Add arguments
    #parser.add_argument("default", nargs="?", default=None, help="default entry")
    parser.add_argument('-b', '--bible', action='store', dest='bible', help="convert Unique Bible App *.bible database; accepts a file or folder path")
    # Parse arguments
    args = parser.parse_args()
    # Get options
    #prompt = args.default.strip() if args.default and args.default.strip() else ""

    if givenPath := args.bible.strip():
        if os.path.isfile(givenPath):
            ConvertBible.convert_bible(givenPath)
        elif os.path.isdir(givenPath):
            for i in os.listdir(givenPath):
                iFile = os.path.join(givenPath, i)
                if os.path.isfile(iFile) and iFile.endswith(".bible"):
                    ConvertBible.convert_bible(iFile)


if __name__ == '__main__':
    main()