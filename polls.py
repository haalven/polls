#!/usr/bin/env python3

# NY Times presidential approval poll data

DEBUG_LEVEL = 1

import sys, os.path, tomllib, urllib.request, csv
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
    if DEBUG_LEVEL: print(c(196) + str(msg) +f(0),
                          file=sys.stderr)

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

# get URL
def get_url(url):
    try:
        with urllib.request.urlopen(url) as r:
            return r.read().decode('utf-8')
    except Exception as e:
        warn('urlopen error: ' + str(e))
        return None

def main() -> int:
    # my path
    my_path = os.path.abspath(__file__)
    my_dir  = os.path.dirname(my_path)
    my_name = os.path.basename(my_path)

    # load configuration file
    config = read_configuration(my_dir, my_name)
    if DEBUG_LEVEL > 0: print('csvurl:', config['csvurl'])

    # download csv file
    csvdata = get_url(config['csvurl'])
    if not csvdata: return 'error: csv download failed'

    #read csv file
    csvreader = csv.reader(csvdata.splitlines(), delimiter=',')

    # header
    header = next(csvreader)

    # prepare lists
    poll_dates = []
    poll_yes, poll_no = [], []

    # find columns
    date_col = header.index('end_date')
    pollster_col = header.index('pollster')
    yes_col = header.index('yes')
    no_col = header.index('no')

    # csv reader
    for row in csvreader:
        # check pollster
        if str(row[pollster_col]).strip() not in config['selected_pollsters']:
            continue
        # fill lists
        poll_dates.append(dt.strptime(row[date_col], '%m/%d/%y'))
        poll_yes.append(float(row[yes_col]))
        poll_no.append(float(row[no_col]))

    # calculate margins
    poll_margin = [poll_yes[i] - poll_no[i] for i in range(len(poll_yes))]

    # move to pandas DataFrame
    df = pd.DataFrame({'date': pd.to_datetime(poll_dates), 'margin': poll_margin})

    # sort by date
    df = df.sort_values('date')

    # LOWESS smoothing
    smoothed = sm.nonparametric.lowess(df['margin'], df['date'], frac=1)

    # setup matplotlib
    fig, ax = plt.subplots()
    # title & footnote
    plt.title('Trump Approval minus Disapproval (%)')
    fig.text(0.01, 0.01, 'source: https://www.nytimes.com/interactive/polls/donald-trump-approval-rating-polls.html', fontsize=7, color='gray')

    # margin scatter
    ax.scatter(poll_dates, poll_margin, label='Margin', marker='D', s=66, color='navy', alpha=0.5)
    # trend line
    plt.plot(df['date'], smoothed[:, 1], '-', label='Trend', color='navy', linewidth=25, alpha=0.1)
    # limits and zero line
    ax.set(ylim=(-20, 15))
    plt.axhline(0, color='black', linewidth=1)

    # autoformat dates
    plt.gcf().autofmt_xdate()

    # scale up
    plt.rcParams['savefig.dpi'] = 300
    # show plot
    plt.show()

    return 0

if __name__ == '__main__':
    sys.exit(main())
