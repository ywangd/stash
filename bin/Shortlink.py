import requests
import argparse
import sys
def main(args):
    print("-url {0}".format(args.id))
def url():
    long_url = inp
    querystring = {"url":long_url}
    url = "http://suo.im/api.php"
    response = requests.request("GET", url, params=querystring)
    print(response.text)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(usage="it's usage tip.", description="help info.")
    parser.add_argument("-url", type=str, required=True, help="The Origin URL.")
    args = parser.parse_args()
    main(args)
    inp = args.inp
    url()
