from psycopg2 import connect
from datetime import date
import matplotlib.pyplot as plt
from datetime import datetime
import requests


class Persistence:
    def __init__(self):
        self.days_per_month = dict()

        self.days_per_month[1] = 31
        self.days_per_month[2] = 28
        self.days_per_month[3] = 31
        self.days_per_month[4] = 30
        self.days_per_month[5] = 31
        self.days_per_month[6] = 30
        self.days_per_month[7] = 31
        self.days_per_month[8] = 31
        self.days_per_month[9] = 30
        self.days_per_month[10] = 31
        self.days_per_month[11] = 30
        self.days_per_month[12] = 31

        self.url_appendices = dict()

        self.url_appendices['El'] = 'V'
        self.url_appendices['G'] = 'W'
        self.url_appendices['S0'] = 'Z'

        self.start_day = 0
        self.start_month = 0
        self.start_year = 0

        self.user = None

    @staticmethod
    def make_connection():
        conn = connect(host="localhost", database="YouLessMonitor", user="YouLessAdmin", password="admin")
        return conn

    def set_user(self, user):
        self.user = user

    # this function will update the data in the weeks databases
    # this function is called with a delta, which is an integer in the range of [0,7],
    #                         a postfix, which is the database it needs to be added to
    #                         and an ip, which is the ip of the YouLess server
    def update_weeks(self, delta, postfix, ip):
        connection = self.make_connection()
        cursor = connection.cursor()

        cursor.execute('DELETE FROM "Week_{}"'.format(postfix))

        for day in reversed(range(delta)):
            html = requests.get("http://{}/{}?d={}".format(ip, self.url_appendices[postfix], day + 1)).text
            html = html.split("\n")
            html.pop(0)
            html.pop(-1)
            for entry in html:
                # read the data
                date = entry.split(" ")[0]
                hour = entry.split(" ")[1].split(":")[0]
                result = entry.split(" ")[-1]

                # account for missing data
                if result == '*':
                    result = 0

                # remove , separation
                result = int(str(result).replace(',', ''))

                # split date
                day = date.split("-")[0]
                month = date.split("-")[1]
                year = "20" + date.split("-")[2]

                cursor.execute('INSERT INTO "Week_{}" VALUES ({}, {}, {}, {}, {})'
                               .format(postfix, day, month, year, hour, result))

        connection.commit()

    def plot_week(self, postfix, y_label):
        connection = self.make_connection()
        cursor = connection.cursor()

        cursor.execute('SELECT year, month, day, hour, {} from "Week_{}"'.format(y_label, postfix))
        results = cursor.fetchall()

        dates = list()
        date_labels = list()
        watts = list()
        i = 0

        while i < len(results):
            result = results[i]
            temp = datetime(result[0], result[1], result[2], result[3])
            dates.append(temp)
            watts.append(result[4])
            date_labels.append("{}-{}:{}".format(result[1], result[2], result[3]))

            i += 2

        plt.figure(figsize=(18, 9))
        plt.bar(dates, watts, align='edge', width=0.05)
        plt.xlabel('Dates')
        plt.ylabel(y_label)
        for index in range(0, len(dates), 12):
            plt.axvline(dates[index], color='r')
        plt.xticks(dates, date_labels, rotation='vertical')
        plt.tight_layout()
        plt.savefig('static/plots/week_plot_{}.png'.format(postfix))

    # this function will update the data in the weeks databases
    # this function is called with a month, which is the index of the month,
    #                         the number of days there are in the current month,
    #                         a postfix, which is the database it needs to be added to
    #                         and an ip, which is the ip of the YouLess server
    def update_year(self, month, days, postfix, ip):
        connection = self.make_connection()
        cursor = connection.cursor()

        cursor.execute('DELETE FROM "Year_{}"'.format(postfix))

        past_month = month - 1
        if past_month == 0:
            past_month = 12

        html = requests.get("http://{}/{}?m={}".format(ip, self.url_appendices[postfix], past_month)).text
        html = html.split("\n")
        html.pop(0)
        html.pop(-1)
        del html[:-(self.days_per_month[past_month] - days)]

        html2 = requests.get("http://{}/{}?m={}".format(ip, self.url_appendices[postfix], month)).text
        html2 = html2.split("\n")
        html2.pop(0)
        html2.pop(-1)

        html += html2

        for entry in html:
            # read the data
            date = entry.split(" ")[0]
            result = entry.split(" ")[-1]

            # account for missing data
            if result == '*':
                result = 0

            # remove , separation
            result = int(str(result).replace(',', ''))

            # split date
            day = int(date.split("-")[0])
            month = int(date.split("-")[1])
            year = int(date.split("-")[2]) + 2000

            if year < self.start_year or (year == self.start_year and month < self.start_month) or \
                    (year == self.start_year and month == self.start_month and day < self.start_day):
                continue

            cursor.execute('INSERT INTO "Year_{}" VALUES ({}, {}, {}, {})'
                           .format(postfix, day, month, year, result))

        connection.commit()

    def plot_month(self, postfix, y_label):
        connection = self.make_connection()
        cursor = connection.cursor()

        cursor.execute('SELECT year, month, day, {} from "Year_{}" LIMIT 31'.format(y_label, postfix))
        results = cursor.fetchall()

        dates = list()
        watts = list()
        i = 0

        while i < len(results):
            result = results[i]
            temp = datetime(result[0], result[1], result[2])
            dates.append(temp)
            watts.append(result[3])

            i += 1

        plt.figure(figsize=(18, 9))
        plt.bar(dates, watts, align='edge', width=0.5)
        plt.xlabel('Dates')
        plt.ylabel(y_label)
        plt.xticks(dates, rotation='vertical')
        plt.tight_layout()
        plt.savefig('static/plots/month_plot_{}.png'.format(postfix))

    def plot_year(self, postfix, y_label):
        connection = self.make_connection()
        cursor = connection.cursor()

        query = "SELECT year, month , SUM(" + y_label + ") as " + y_label + ", COUNT(month) as count from \"Year_"
        query += postfix + "\" group by year, month"

        cursor.execute(query)
        results = cursor.fetchall()

        dates = list()
        watts = list()
        date_labels = list()
        i = 0

        print(results)

        while i < len(results):
            result = results[i]
            temp = datetime(result[0], result[1], 1)
            date_labels.append("{}-{}".format(result[0], result[1]))
            dates.append(temp)
            watts.append(result[2]/result[3])

            i += 1

        plt.figure(figsize=(18, 9))
        plt.bar(dates, watts, align='edge', width=2)
        plt.xlabel('Dates')
        plt.ylabel(y_label)
        plt.xticks(dates, date_labels, rotation='vertical')
        plt.tight_layout()
        plt.savefig('static/plots/year_plot_{}.png'.format(postfix))

    def update(self, user_id):
        connection = self.make_connection()
        cursor = connection.cursor()

        # get current date
        today = date.today()
        temp_vals = today.__str__().split("-")
        year = int(temp_vals[0])
        month = int(temp_vals[1])
        day = int(temp_vals[2])

        cursor.execute('SELECT start, ip FROM "Users" WHERE id = \'{}\''.format(ord(user_id)))

        # get start date
        result = cursor.fetchone()
        start = result[0].__str__().split("-")
        start_year = int(start[0])
        start_month = int(start[1])
        start_day = int(start[2])

        self.start_year = start_year
        self.start_month = start_month
        self.start_day = start_day

        # get ip
        ip = result[1]

        # calculated the evaluated difference
        delta_year = year - start_year
        delta_month = month - start_month + delta_year * 365
        delta_day = day - start_day + delta_year * 365

        # add the days for the past months
        for past_month in range(month - start_month):
            delta_day += self.days_per_month[past_month + 1]

        # account for leap years
        temp = delta_month - year % 4
        while temp >= 0:
            delta_day += 1
            temp -= 4

        # number of days in evaluated week
        passed_days = min(delta_day, 7)

        if self.user.track_el:
            self.update_weeks(passed_days, "El", ip)
            self.update_year(month, day, "El", ip)
            self.plot_week("El", "watt")
            self.plot_month("El", "watt")
            self.plot_year("El", "watt")

        if self.user.track_g:
            self.update_weeks(passed_days, "G", ip)
            self.update_year(month, day, "G", ip)
            self.plot_week("G", "liters")
            self.plot_month("G", "liters")
            self.plot_year("G", "liters")

        if self.user.track_s0:
            self.update_weeks(passed_days, "S0", ip)
            self.update_year(month, day, "S0", ip)
            self.plot_week("S0", "watt")
            self.plot_month("S0", "watt")
            self.plot_year("S0", "watt")

    def evaluate_statistics(self):
        connection = self.make_connection()
        cursor = connection.cursor()

        cursor.execute('SELECT query, name, columns from "Statistics"')
        queries = cursor.fetchall()

        for i in range(len(queries)):
            query = queries[i]
            cursor.execute(query)
            result = cursor.fetchall

            queries[i] = queries[i] + result

        return queries

    def add_query(self, query, name, columns):
        connection = self.make_connection()
        cursor = connection.cursor()

        cursor.execute('INSERT INTO "Statistics" VALUES({}, {}, {})'.format(query, name, columns))
        connection.commit()