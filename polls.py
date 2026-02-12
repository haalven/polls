#!/usr/bin/env python3

# NY Times presidential approval poll data

DEBUG_LEVEL = 1

import argparse, sys, os.path, tomllib
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt
from datetime import datetime as dt

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
    parser.add_argument('-s', '--show',
                        action='store_true',
                        required=False,
                        help='show data points')
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
        warn('error reading csv data from: ' + config['csvurl'] + ' failed: ' + str(e))
        return 1
    # save csv file
    today = dt.now().date().isoformat()
    data_file = os.path.splitext(my_name)[0] + '-original-' + today + '.csv'
    df.to_csv(os.path.join(my_dir, data_file), index=False)

    # select columns
    polldata = df[['end_date', 'poll_id', 'pollster', 'state', 'politician', 'yes', 'no']]
    polldata = polldata.copy()

    # filter for US polls
    polldata = polldata[polldata['state'] == 'US']
    # filter for politician
    polldata = polldata[polldata['politician'] == 'Donald Trump']

    # filter for selected pollsters
    print(f(1) + 'data set:' + f(0))
    if config['selected_only'] and not arguments.all:
        print(' selected quality pollsters')
        polldata = polldata[polldata['pollster'].isin(config['selected_pollsters'])]
    else:
        print(' all pollsters (bad quality)')
    # source link
    print(f(1) + 'source:' + f(0))
    print(config['nyturl'])

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

    # LOWESS regression
    frac = .35 if (config['selected_only'] and not arguments.all) else .3
    lowess = sm.nonparametric.lowess(polldata['margin'], polldata['dt_date'], frac=frac)
    trend = lowess[:, 1]
    print(f(1) + 'latest regression:' + f(0))
    print(trend[-1])
    # save regression
    today = dt.now().date().isoformat()
    data_file = os.path.splitext(my_name)[0] + '-regression-' + today + '.csv'
    regr_df = pd.DataFrame({'Date': polldata['dt_date'], 'Pollster': polldata['pollster'], 'Margin': polldata['margin'], 'Regression': trend, 'Diff': polldata['margin']-trend})
    # round and reverse
    regr_df = regr_df.round(1).iloc[::-1]
    regr_df.to_csv(os.path.join(my_dir, data_file), index=False)

    # show data points
    if arguments.show:
        os.system(f'vd {os.path.join(my_dir, data_file)}')
        return 0

    # setup matplotlib
    fig, ax = plt.subplots(figsize=(6, 6))
    # title & footnote
    plt.title('Trump 2nd Term Polls: Margin (%)')
    #fig.text(0.01, 0.01, 'source: ' + config['nyturl'], fontsize=7, color='gray')
    fig.text(0.01, 0.01, 'CNN/SSRS, Gallup, Ipsos, NYT/Siena, Pew, Quinnipac', fontsize=7, color='gray')

    # y-limits and horizontal lines
    ax.set(ylim=(-30, 10))
    plt.axhline(0, color='black', linewidth=1)
    for y in (-10, -20, -30):
        plt.axhline(y, color='lightgrey', linewidth=1)

    # pollster lines
    pollster_colors = {
        'CNN/SSRS': '#E41A1C',
        'Gallup': '#377EB8',
        'Ipsos': '#4DAF4A',
        'Pew Research Center': '#984EA3',
        'Quinnipiac University': '#FF7F00',
        'The New York Times/Siena University': '#A65628',
    }
    for pollster, color in pollster_colors.items():
        pollster_data = polldata[polldata['pollster'] == pollster]
        if not pollster_data.empty:
            ax.plot(
                pollster_data['dt_date'],
                pollster_data['margin'],
                '-',
                color=color,
                linewidth=1.2,
                alpha=0.8,
            )

    # margin scatter
    ax.scatter(polldata['dt_date'], polldata['margin'], label='Margin', marker='D', s=25, color='gray', alpha=0.33)

    # trend line
    plt.plot(polldata['dt_date'], trend, '-', label='Trend', color='#000000', linewidth=4, alpha=0.9)

    # autoformat dates
    plt.gcf().autofmt_xdate()

    # scale up
    plt.rcParams['savefig.dpi'] = 300
    # show plot
    plt.show()

    return 0

if __name__ == '__main__':
    sys.exit(main())
