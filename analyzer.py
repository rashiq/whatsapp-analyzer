import sys
import numpy as np
import datetime as dt

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.colors as clrs
import matplotlib.dates as mdts
import matplotlib.ticker as mtick
import matplotlib.patches as mpatches

from math import log
from random import sample
from scipy.interpolate import interp1d


# chat file
FILE = sys.argv[1] if len(sys.argv) > 1 else 'chat.txt'
# colors used when plotting message trend
TRND_THEME = ['#b0b0b0', '#07a0c3', '#e3170a']
# colors used when plotting user specific information
BACK = '#dddddd'
SPEC_THEME = ['#d3d3d3', '#a9a9a9', '#588c7e', '#f2e394', '#f2ae72', '#d96459', '#8c4646']
# colors used when plotting general user information
GNRL_THEME = ['#c7c6c1', '#5398d9', '#ff0000', '#00ff00']


class Member:
    """Represent a chat participator"""

    # TODO
    # - make smallest first value static
    # - save len(days) as static value
    # - alle themes zu einem zusammenfassen
    # - variablen in dieser Klasse umbenennen für mehr klarheit
    # - Farbe der User in den Usern speichern?
    # - member list mit dem aktivsten chatteilnehmer als erstes ordnen

    def __init__(self, name, first, period):
        """Initializes object and sets variables to default values"""
        self.name = name
        self.words = {}
        self.hours_mg = [[0 for _ in range(24)] for _ in range(7)]  # messages in hour at weekday
        self.hours_wd = [[0 for _ in range(24)] for _ in range(7)]  # words in hour at weekday
        self.days = [0 for _ in range(period)]  # messages mapped on days
        self.first = first  # date of first message
        self.media = 0  # number of media files sent

    def add_message(self, message, day, weekday, hour):
        """Adds message data to the user object"""
        self.hours_mg[weekday][hour] += 1
        self.days[day] += 1
        # excluded words
        excl = ['<image', '<video', '<‎GIF', 'omitted>']
        # strip words of dots, quotation marks etc.
        for word in message.split():
            self.hours_wd[weekday][hour] += 1
            word = word.lower()
            while len(word) > 1 and word[-1] in '*-,."\'!?:—_':
                word = word[:-1]
            while len(word) > 1 and word[0] in ',."\'*(-—~#/_':
                word = word[1:]
            if word not in excl:
                self.words.setdefault(word, 0)
                self.words[word] += 1
            elif word == 'omitted>':
                self.media += 1


class Chat:
    """Represent the chat data"""

    def __init__(self, path):
        """Initializes object and reads the chat file"""
        chfile = open(path, 'r')
        self.chat = chfile.readlines()
        chfile.close()

    @staticmethod
    def strdate(s):
        """Extract date and hour out of given string"""
        return dt.date(2000+int(s[6:8]), int(s[3:5]), int(s[:2])), int(s[10:12])

    @staticmethod
    def shftfive(date, hour):
        """Shift date so that one day starts and ends at 4 in the morning"""
        return date - dt.timedelta(days=1) if hour < 4 else date

    @staticmethod
    def idf(word, members):
        """Calculate idf value for word in members"""
        return log(len(members) / len([m for m in members if word in m.words]))

    def _rmnl(self):
        """Remove newline chars from messages"""
        res = []
        prev = None
        for msg in self.chat:
            # check for correct formatting
            if len(msg) > 20 and msg[2] == msg[5] == '.' and msg[8:10] == ', ' and msg[12] == msg[15] == msg[18] == ':':
                if prev: res.append(prev)
                prev = msg
            else:
                if prev: prev = prev[:-1] + ' ' + msg
        res.append(prev)
        self.chat = res

    def process(self):
        """Order and prepare data for plotting"""
        self._rmnl()
        # initialize vars
        members = []
        first = Chat.shftfive(*Chat.strdate(self.chat[0]))
        period = (Chat.shftfive(*Chat.strdate(self.chat[-1])) - first).days + 1
        # process messages
        for line in self.chat:
            try:
                hour = int(line[10:12])
                date = Chat.shftfive(*Chat.strdate(line))
                line = line[20:]
                name = line[:line.index(':')]
                line = line[line.index(': ') + 2:]
            except ValueError:
                pass  # ignore corrupted messages
            else:
                if all(member.name != name for member in members):
                    members.append(Member(name, date, period))
                for member in members:
                    if member.name == name:
                        member.add_message(line, (date-first).days, date.weekday(), hour)
        return members


def trend(members):
    """Visualize overall message count trend.

    This includes raw message count/day, mean count/day for every
    month and overall mean count/day.
    """
    period = len(members[0].days)
    days = [sum(m.days[i] for m in members) for i in range(period)]
    first = min(m.first for m in members)
    dates = [first + dt.timedelta(days=i) for i in range(period)]

    # convert from daily message count to monthly average
    start = first if first.day==1 else first.replace(day=1, month=first.month+1)
    delta_months = (
        ((first + dt.timedelta(days=period)).year - start.year) * 12
        + (first + dt.timedelta(days=period)).month
        - start.month
    )
    # get indexes of first day of every month in days list
    indexes = [(start-first).days] + [(start.replace(
        month=(start.month+i) % 12 + 1,
        year=start.year + (start.month+i) // 12
    ) - first).days for i in range(0, delta_months)]
    # get monthly messages/day mean
    months = [np.mean(days[indexes[i]:indexes[i+1]]) for i in range(len(indexes)-1)]

    # plot total messages per day
    plt.figure()
    stemline = plt.stem(dates, days, markerfmt=' ', basefmt=' ', label='Total Messages per Day')[1]
    plt.setp(stemline, linewidth=0.5, color=TRND_THEME[0])
    # plot overall mean of messages day
    mean = np.mean(days)
    plt.axhline(mean, color=TRND_THEME[2], label='Overall Mean of Messages per Day')
    # plot monthly mean of messages per day
    x = [dates[i] for i in indexes[:-1]]
    plt.plot(x, months, color=TRND_THEME[1], label='Monthly Mean of Messages per Day')

    # set style attributes
    plt.gca().yaxis.grid(True)
    plt.legend()
    plt.title('Messages per Day')

    # annotate mean line
    plt.annotate(
        '{0:.{digits}f}'.format(mean, digits=2),
        xy=(min(m.first for m in members) + dt.timedelta(days=period-1), mean),
        xytext=(8, -3),
        textcoords='offset points',
    )
    # annotate maxima
    maxima = sorted(days, reverse=True)[:3]
    annotations = [(dates[days.index(m)], m) for m in maxima]
    for a in annotations:
        plt.annotate(
            a[0].strftime('%d.%m.%Y'),
            xy=a,
            xytext=(-10, -6),
            rotation=90,
            textcoords='offset points',
        )


def activity(members):
    """Visualize member activity over whole chat period.

    Display weekly means for every user multiple times in line charts
    emphasizing one user at a time.
    """
    period = len(members[0].days)
    days = [sum(m.days[i] for m in members) for i in range(period)]
    first = min(m.first for m in members)

    # define subplots
    fig, axarr = plt.subplots(len(members), sharex=True, sharey=True)
    # compute weekly means
    index = (7 - first.weekday()) % 7
    weeks = [
        [np.mean(members[i].days[k:k+7]) for k in range(index, period, 7)]
        for i in range(len(members))
    ]
    dates = [first + dt.timedelta(days=i) for i in range(index, period, 7)]

    # plot multiple times with different emphasis
    for i in range(len(members)):
        for j in range(len(members)):
            axarr[i].plot(dates, weeks[j], color=BACK, linewidth=0.5)
        axarr[i].plot(dates, weeks[i], color=SPEC_THEME[i])
        # set style attributes
        axarr[i].yaxis.grid(True)
        axarr[i].set_ylabel(members[i].name, labelpad=20, rotation=0, ha='right')

    # set title
    fig.add_subplot(111, frameon=False)
    plt.tick_params(labelcolor='none', left=False, bottom=False)
    plt.title('User Activity (Weekly Messages / Day Means)')


def shares(members):
    """Visualize conversation shares.

    This includes number of messages as share, number of words as share
    and average words per message.
    """
    fig = plt.figure()

    # plot stacked bar plots visualizing shares of messages, text and media files
    count = [
        [sum(m.days) for m in members],
        [sum(m.words.values()) for m in members],
        [m.media for m in members]
    ]
    for i in range(3):
        ax = fig.add_subplot(161 + i, xlim=[0, 1])
        c = count[i]
        total = sum(c)
        shares = [c / total for c in c]
        for j in range(len(members)):
            x = plt.bar(0.6, shares[j], 0.6, bottom=sum(shares[:j]), color=SPEC_THEME[j])
            p = x.patches[0]
            # annotate segment with total value
            if p.get_height() > 0.03:
                ax.text(
                    p.get_x() + p.get_width() / 2,
                    p.get_y() + p.get_height() / 2,
                    c[j],
                    ha='center',
                    va='center',
                )

        # set style attributes
        ax.spines['bottom'].set_visible(False)
        ax.tick_params(direction='inout', length=10)
        ax.xaxis.set_visible(False)
        ax.set_yticks([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        if i: ax.set_yticklabels([])
        else: ax.set_yticklabels(['{:.0f}%'.format(x*100) for x in plt.gca().get_yticks()])
        ax.text(
            p.get_x() + p.get_width() / 2,
            -0.04,
            ('Messages Sent', 'Words Written', 'Media Files Sent')[i],
            ha='center'
        )

    # set title
    fig.add_subplot(121, frameon=False)
    plt.tick_params(labelcolor='none', left=False, bottom=False)
    plt.title('Shares of Messages, Words and Media Files')

    # plot overall mean of number of words per message
    ax = fig.add_subplot(222, ylim=[-1, len(members)])
    mean = sum([sum(m.words.values()) for m in members]) / sum([sum(m.days) for m in members])
    plt.axvline(mean, color=TRND_THEME[2], label='Overall Mean', zorder=0)
    plt.legend()

    # plot average number of words per message
    averages = [sum(m.words.values()) / sum(m.days) for m in members]
    plt.barh(range(len(members)), averages, 0.5, color=SPEC_THEME)
    plt.title('Average Words per Message')

    # TODO annotate mean line

    # set style attributes
    ax.xaxis.grid(True)
    ax.yaxis.set_visible(False)

    # annotate with exact values
    for i in range(len(members)):
        plt.text(
            averages[i] + max(averages) * 0.02,
            i,
            '{0:.{digits}f}'.format(averages[i], digits=2),
            ha='left',
            va='center',
        )

    # display legend
    fig.add_subplot(224, frameon=False)
    plt.tick_params(labelcolor='none', left=False, bottom=False)
    patches = [mpatches.Patch(label=m.name, color=c) for m, c in zip(members, SPEC_THEME)]
    plt.legend(handles=patches[::-1], loc=10)


def weekday_avg(members):
    """plot message count average on specific day of the week"""
    period = len(members[0].days)
    wd_sum_msgs = [sum([sum(m.hours_mg[i]) for m in members]) for i in range(7)]
    frst = min([m.first for m in members])
    frst_wd = frst.weekday()  # weekday of first message
    last_wd = (frst + dt.timedelta(days=period-1)).weekday()  # weekday of last message
    wd_count = [(period - last_wd - 1) // 7 for _ in range(7)]
    for i in range(7, (frst_wd if frst_wd else 7), -1):
        wd_count[i-1] += 1
    for i in range(last_wd+1):
        wd_count[i] += 1
    wd_avg_msgs = tuple(map(lambda e, a: e / a, wd_sum_msgs, wd_count))
    plt.bar(range(7), wd_avg_msgs, align='center', color=GNRL_THEME[0])
    # limiters, xticks, labels
    wds = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    plt.xticks(range(7), wds)
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().tick_params(top=False, right=False)
    plt.gca().xaxis.grid(False)
    plt.title('Average Messages per Weekday')
    plt.ylabel('# Messages')


def hour_avg(members):
    """Visualizes message count average on specific hour of the day"""
    period = len(members[0].days)
    x = np.linspace(0, 24, num=180, endpoint=True)
    # days are defined to start at 4 in the morning
    overall = [e / period for e in (sum((sum((m.hours_mg[i][j] for i in range(7))) for m in members)) for j in range(24))]
    overall = overall[4:] + overall[:5]
    # get midweek (mon, tue, wen, thu) hours
    midweek = [e / (period*4/7) for e in (sum((sum((m.hours_mg[i][j] for i in range(4))) for m in members)) for j in range(24))]
    midweek = midweek[4:] + midweek[:5]
    # get weekend (fri, sat, sun) hours
    weekend = [e / (period*3/7) for e in (sum((sum((m.hours_mg[i][j] for i in range(4, 7))) for m in members)) for j in range(24))]
    weekend = weekend[4:] + weekend[:5]
    # cubic interpolate
    f = interp1d(range(25), overall, kind='cubic')
    g = interp1d(range(25), midweek, kind='cubic')
    h = interp1d(range(25), weekend, kind='cubic')
    # plot
    plt.plot(x, f(x), GNRL_THEME[1], ls='-', lw=2)
    plt.plot(x, g(x), GNRL_THEME[2], ls='--', lw=2)
    plt.plot(x, h(x), GNRL_THEME[3], ls='--', lw=2)
    # limiters, ticks, labels, legend
    plt.xticks(range(25), [i for i in range(4, 24)] + [i for i in range(5)])
    plt.xlim([-1, 25])
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    plt.gca().tick_params(top=False, right=False)
    plt.title('Average Messages per Hour of the Day')
    plt.xlabel('Hour of the Day')
    plt.ylabel('# Messages')
    plt.legend(['Overall', 'Midweek (Mo,Tu,We,Th)', 'Weekend (Fr,Sa,Su)'], loc=2)


def worduse_md(members, path='worduse.md'):
    """Generates markdown document with most used and most important (tf-idf) words for each user"""
    with open(path, 'w') as mdfile:
        for m in sorted(members, key=lambda e: len(e.words), reverse=True):
            mdfile.write('# ' + m.name + '\nMost used words | Frequency in messages | Most important (tf-idf) words | Frequency in messages\n-|-|-|-\n')
            most_used = sorted(m.words.items(), key=lambda e: e[1], reverse=True)[:15]
            avg_per_msg_used = [wd[1] / sum(m.days) for wd in most_used]
            most_impt = sorted(m.words.items(), key=lambda x: x[1] * Chat.idf(x[0], members), reverse=True)[:15]
            avg_per_msg_impt = [wd[1] / sum(m.days) for wd in most_impt]
            for wd_used, avg_used, wd_impt, avg_impt in zip(most_used, avg_per_msg_used, most_impt, avg_per_msg_impt):
                mdfile.write(wd_used[0] + ' | ' + '{0:.3f}'.format(avg_used) + ' | ' + wd_impt[0] + '| {0:.3f}'.format(avg_impt) + '\n')


if __name__ == '__main__':
    chat = Chat(FILE)
    members = sorted(chat.process(), key=lambda m: sum(m.days))
    SPEC_THEME = SPEC_THEME[len(SPEC_THEME)-len(members):] if len(members) <= len(SPEC_THEME) else sample(list(clrs.cnames), len(members))

    # set custom plot style
    plt.style.use('style.mplstyle')

    # show plots
    plots = [trend, activity, shares]  # [trend, activity, message_count, message_count_pie, word_count, word_count_pie, mediacount, weekday_avg, hour_avg]
    for plot in plots:
        plot(members)
        plt.gcf().canvas.set_window_title('Whatsapp Analyzer')
        plt.show(block=False)
    plt.show()

    # Uncomment for generating a markdown file containing worduse statistics
    # worduse_md(members)

