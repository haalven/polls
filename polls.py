#!/usr/bin/env python3

# NY Times presidential approval poll data

DEBUG_LEVEL = 1

import argparse, sys, os.path, tomllib
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

# xterm formatting
def f(code): return '\x1B[' + str(code) + 'm'
def c(code): return f('38;5;' + str(code))

# warnings
def warn(msg):
    global DEBUG_LEVEL
    if DEBUG_LEVEL:
        print(c(196) + str(msg) +f(0), file=sys.stderr)

# read TOML file
def read_configuration(my_dir, my_name):
    c_file = os.path.splitext(my_name)[0] +'.toml'
    c_path = os.path.join(my_dir, c_file)
    if not os.path.exists(c_path):
        warn('config not found at: ' + c_path)
        return None
    try:
        with open(c_path, 'rb') as f:
            return tomllib.load(f)
    except:
        warn('error reading toml: ' + c_path)
        return None

# parse arguments
def get_arguments(my_name):
    parser = argparse.ArgumentParser(prog=my_name)
    parser.add_argument('-a', '--all',
                        action='store_true',
                        required=False,
                        help='use all pollsters')
    return parser.parse_args()


def main() -> int:
    # my path
    my_path = os.path.abspath(__file__)
    my_dir  = os.path.dirname(my_path)
    my_name = os.path.basename(my_path)

    # load configuration file
    config = read_configuration(my_dir, my_name)

    # parse arguments
    arguments = get_arguments(my_name)

    # read csv file (pandas)
    try:
        df = pd.read_csv(config['csvurl'])
    except Exception as e:
        return 'error: csv download failed: ' + str(e)

    # select columns
    polldata = df[['end_date', 'poll_id', 'pollster', 'politician', 'yes', 'no']]
    polldata = polldata.copy()

    # filter for politician
    polldata = polldata[polldata['politician'] == 'Donald Trump']

    # filter for selected pollsters
    if config['selected_only'] and not arguments.all:
        polldata = polldata[polldata['pollster'].isin(config['selected_pollsters'])]

    # remove duplicates
    poll_ids = []
    for i, row in polldata.iterrows():
        poll_id = row['poll_id']
        if poll_id in poll_ids:
            polldata.drop(i, inplace=True)
        poll_ids.append(poll_id)

    # calculate margins
    polldata['margin'] = polldata['yes'] - polldata['no']

    # add dt-dates
    polldata['dt_date'] = pd.to_datetime(polldata['end_date'], format='%m/%d/%y')
    # sort by date
    polldata = polldata.sort_values('dt_date')

    # print data
    print(f(1) + 'lastest polls:' + f(0))
    print(polldata[['dt_date', 'pollster', 'margin']].tail(15))

    # LOWESS smoothing
    lowess = sm.nonparametric.lowess(polldata['margin'], polldata['dt_date'], frac=.67)
    trend = lowess[:, 1]

    # setup matplotlib
    fig, ax = plt.subplots()
    # title & footnote
    plt.title('Trump Approval minus Disapproval (%)')
    fig.text(0.01, 0.01, 'source: ' + config['nyturl'], fontsize=7, color='gray')

    # limits and zero line
    ax.set(ylim=(-30, 20))
    plt.axhline(0, color='black', linewidth=1)

    # margin scatter
    ax.scatter(polldata['dt_date'], polldata['margin'], label='Margin', marker='D', s=33, color='gray', alpha=0.33)
    # trend line
    plt.plot(polldata['dt_date'], trend, '-', label='Trend', color='deepskyblue', linewidth=2.5, alpha=0.9)

    # autoformat dates
    plt.gcf().autofmt_xdate()

    # scale up
    plt.rcParams['savefig.dpi'] = 300
    # show plot
    plt.show()

    return 0

if __name__ == '__main__':
    sys.exit(main())
