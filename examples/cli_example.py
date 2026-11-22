"""A standalone example of literal argparse declarations."""
import argparse

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('-h', '--help', action='help')
parser.add_argument('--verbose', action='store_true')
parser.add_argument('--output')
parser.add_argument('--legacy', action='store_true')
