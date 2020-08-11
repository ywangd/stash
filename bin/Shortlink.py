import requests
import argparse
import sys
def main(args):
    print("-url {0}".format(args.url))
def url():
    long_url = inpu
    querystring = {"url":long_url}
    url = "http://suo.im/api.php"
    param={"url":"inpu","key":"5f3252d6b1b63c5aeec52d18@0e52d0179c9d30bfbc945b11581a0f76"}
    response = requests.request("GET", url, params=param)
    print(response.text)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(usage="it's usage tip.", description="help info.")
    parser.add_argument("-url", type=str, required=True, help="The Origin URL.")
    args = parser.parse_args()
    main(args)
    inpu = args.url
    url()
