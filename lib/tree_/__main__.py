import sys
from tree import main

if __name__ == "__main__":
    # sys.argv = [
    #     "tree",
    #     "..",
    #     "-a",
    #     "-L", "4",
    #     "-I", r'\.\*',
    #     "-f",
    #     "--ignore-case",
    #     "--charset", "utf-8-old",
    #     "--filelimit", "20",
    #     #"--timefmt", "%y.%M",
    #     #"--noreport"
    #     #"-o", "log.txt",
    #     #"-Q",
    #     "-p",
    #     "-u",
    #     "-s",
    #     "-h",
    #     "-si",
    #     "-D",
    #     #"-F",
    #     "-C",
    # ]
    main(sys.argv[1:])
