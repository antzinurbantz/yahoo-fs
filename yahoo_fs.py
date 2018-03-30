#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Yahoo! Finance Scraper
# https://github.com/FredrikBakken/yahoo-fs
#
# Author: Fredrik Bakken
# Version: 0.0.3
# Website: https://www.fredrikbakken.no/

import sys
import math
import calendar
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

PYTHON_VERSION = sys.version_info[0]
if PYTHON_VERSION == 3:
    import urllib.request
else:
    import urllib2


class Share:
    def __init__(self, ticker, loader=None):
        self.ticker = ticker
        self.loader = loader

        self.url_summary = "https://finance.yahoo.com/quote/" + self.ticker
        self.url_statistics = self.url_summary + "/key-statistics?p=" + self.ticker
        self.url_profile = self.url_summary + "/profile?p=" + self.ticker
        self.url_analysts = self.url_summary + "/analysts?p=" + self.ticker

        self.content_summary = self._open_page_content(self.url_summary)
        self.content_statistics = self._open_page_content(self.url_statistics)
        self.content_profile = self._open_page_content(self.url_profile)
        self.content_analysts = self._open_page_content(self.url_analysts)

        self.soup_summary = BeautifulSoup(self.content_summary, 'html.parser')
        self.soup_statistics = BeautifulSoup(self.content_statistics, 'html.parser')
        self.soup_profile = BeautifulSoup(self.content_profile, 'html.parser')
        self.soup_analysts = BeautifulSoup(self.content_analysts, 'html.parser')


    def _open_page_content(self, url):
        if PYTHON_VERSION == 3:
            return urllib.request.urlopen(url).read()
        else:
            return urllib2.urlopen(url).read()


    def _search_soup(self, soup_url, tag, attribute, value):
        return soup_url.find(tag, attrs={attribute : value}).getText()
    
    def _search_soup_html(self, soup_url, tag, attribute, value):
        return soup_url.find(tag, attrs={attribute : value})

    
    def _statistics_search(self, heading, search_for=None):
        table_section = ''
        head_sections = self.soup_statistics.find_all('h2')
        for i in range(len(head_sections)):
            if head_sections[i].getText() == heading:
                table_section = head_sections[i].find_next_sibling()
                break
        
        statistics_search = {}
        tables = table_section.find_all('table')
        for table in tables:
            table_body = table.find('tbody')
            table_rows = table_body.find_all('tr')
            for row in table_rows:
                cells = row.find_all('td')
                if search_for == None:
                    statistics_search[cells[0].find('span').getText()] = cells[1].getText()
                elif cells[0].find('span').getText() == search_for:
                    return cells[1].getText()
        
        if search_for == None:
            return statistics_search
        return None


    def _company_address(self, soup_url, tag, attribute, value):
        company_location = self._search_soup_html(soup_url, tag, attribute, value)
        
        company_address = {}
        element_counter = 0
        for element in company_location:
            element_counter += 1
            if element_counter == 2:
                company_address['street'] = element
            elif element_counter == 6:
                company_address['address'] = element
            elif element_counter == 10:
                company_address['country'] = element
        return company_address

    
    def _key_executives(self, soup_url, tag, attribute, value):
        table = self._search_soup_html(soup_url, tag, attribute, value)
        table_head = table.find('thead').find('tr')
        table_head_row = table_head.find_all('th')

        table_headings = []
        for row in table_head_row:
            table_headings.append(row.getText())

        table_body = table.find('tbody')
        table_rows = table_body.find_all('tr')
            
        key_executive_result = []
        for row in table_rows:
            cols = row.find_all('td')
            current_row = {}
            for i in range(len(cols)):
                current_row[table_headings[i]] = cols[i].getText()
            key_executive_result.append(current_row)

        return key_executive_result


    def _time_setup(self, date, timezone):      # TODO: Add handling for more timezones
        time_offset = ''
        if timezone == 'CEST':
            time_offset = -1
        elif timezone == 'EDT':
            time_offset = 4
        
        return datetime.strptime(date, '%Y-%m-%d') + timedelta(hours=time_offset)


    def _historical_data(self, from_date, to_date=None, day_range=None):
        timezone = self._search_soup(self.soup_summary, 'div', 'id', 'quote-market-notice').split(' ')[4].replace('.', '')
        from_date = self._time_setup(from_date, timezone)
        if not to_date == None:
            to_date = self._time_setup(to_date, timezone)

        urls = []
        if to_date == None:
            timestamp = int(calendar.timegm(from_date.timetuple()))
            url = self.url_summary + "/history?period1=" + str(timestamp) + "&period2=" + str(timestamp) + "&interval=1d&filter=history&frequency=1d"
            urls.append(url)
        elif to_date and day_range == 'days':
            timestamp_from = int(calendar.timegm(from_date.timetuple()))
            url_from = self.url_summary + "/history?period1=" + str(timestamp_from) + "&period2=" + str(timestamp_from) + "&interval=1d&filter=history&frequency=1d"
            urls.append(url_from)

            timestamp_to = int(calendar.timegm(to_date.timetuple()))
            url_to = self.url_summary + "/history?period1=" + str(timestamp_to) + "&period2=" + str(timestamp_to) + "&interval=1d&filter=history&frequency=1d"
            urls.append(url_to)
        elif to_date and day_range == 'range':
            difference = int((to_date - from_date).days)
            
            days_per_run = 120
            number_of_runs = math.ceil(difference / days_per_run)

            for i in range(number_of_runs):
                start_at = days_per_run * i
                end_at   = days_per_run * (i+1)

                start_date = from_date + timedelta(days=start_at)
                end_date   = from_date + timedelta(days=end_at)
                if end_date > to_date:
                    end_date = to_date
                
                timestamp_from = int(calendar.timegm(start_date.timetuple()))
                timestamp_to = int(calendar.timegm(end_date.timetuple()))
                url = self.url_summary + "/history?period1=" + str(timestamp_from) + "&period2=" + str(timestamp_to) + "&interval=1d&filter=history&frequency=1d"
                urls.append(url)

        historic_result = []
        for url in urls:
            content_history = self._open_page_content(url)
            soup_history = BeautifulSoup(content_history, 'html.parser')

            table = soup_history.find('table', attrs={'class': 'W(100%)'})
            table_head = table.find('thead')
            table_head_row = table_head.find_all('th')
            
            table_headings = []
            for row in table_head_row:
                table_headings.append(row.getText().replace('*', ''))

            table_body = table.find('tbody')
            table_rows = table_body.find_all('tr')
            
            for row in table_rows:
                cols = row.find_all('td')
                current_row = {}
                if len(cols) != 2:
                    for i in range(len(cols)):
                        current_row[table_headings[i]] = cols[i].getText().replace(',', '')
                    
                    if not any(current_row[table_headings[0]] == cols[0] for current_row in historic_result) and \
                       not any(current_row[table_headings[i]] == '-' for i in range(1, len(current_row))):
                        historic_result.append(current_row)
                else:
                    current_row['Date'] = cols[0].getText().replace(',', '')
                    current_row['Dividend'] = cols[1].getText().replace(',', '')
                    historic_result.append(current_row)

        if day_range == 'range':
            historic_result = sorted(historic_result, key = lambda x : datetime.strptime(x['Date'], '%b %d %Y'))

        return historic_result

    
    def _analysts_search(self, heading, search_for=None):
        analysts_search_result = {}
        table_headings = []

        all_tables = self.soup_analysts.find_all('table')

        for table in all_tables:
            table_head = table.find('thead')
            table_head_row = table_head.find('tr').find_all('th')
            if heading == table_head_row[0].getText():
                for i in range(1, len(table_head_row)):
                    table_headings.append(table_head_row[i].getText())

                table_body = table.find('tbody').find_all('tr')
                for table_body_row in table_body:
                    table_body_row_cell = table_body_row.find_all('td')
                    analysts_search_result[table_body_row_cell[0].getText()] = {}
                    for j in range(1, len(table_body_row_cell)):
                        analysts_search_result[table_body_row_cell[0].getText()][table_headings[j-1]] = table_body_row_cell[j].getText()

        return analysts_search_result

    
    # Summary
    def get_stock_exchange(self):
        return self._search_soup(self.soup_summary, 'span', 'data-reactid', '9').split(' ')[0]
    
    def get_currency(self):
        return self._search_soup(self.soup_summary, 'span', 'data-reactid', '9').split(' ')[-1]

    def get_price(self):
        return self._search_soup(self.soup_summary, 'span', 'data-reactid', '14')
    
    def get_change(self):
        return self._search_soup(self.soup_summary, 'span', 'data-reactid', '17').split(' ')[0]
    
    def get_percent_change(self):
        return self._search_soup(self.soup_summary, 'span', 'data-reactid', '17').split(' ')[1].replace('(', '').replace(')', '')
    
    def get_previous_trade_time(self):
        return self._search_soup(self.soup_summary, 'div', 'id', 'quote-market-notice').split(' ')[3]
    
    def get_trade_timezone(self):
        return self._search_soup(self.soup_summary, 'div', 'id', 'quote-market-notice').split(' ')[4].replace('.', '')
    
    def get_previous_close(self):
        return self._search_soup(self.soup_summary, 'td', 'data-test', 'PREV_CLOSE-value')
    
    def get_open(self):
        return self._search_soup(self.soup_summary, 'td', 'data-test', 'OPEN-value')
    
    def get_bid(self):
        return self._search_soup(self.soup_summary, 'td', 'data-test', 'BID-value')
    
    def get_ask(self):
        return self._search_soup(self.soup_summary, 'td', 'data-test', 'ASK-value')

    def get_day_range(self):
        return self._search_soup(self.soup_summary, 'td', 'data-test', 'DAYS_RANGE-value')
    
    def get_52_week_range(self):
        return self._search_soup(self.soup_summary, 'td', 'data-test', 'FIFTY_TWO_WK_RANGE-value')
    
    def get_volume(self):
        return self._search_soup(self.soup_summary, 'td', 'data-test', 'TD_VOLUME-value').replace(',', '')
    
    def get_avg_daily_volume(self):
        return self._search_soup(self.soup_summary, 'td', 'data-test', 'AVERAGE_VOLUME_3MONTH-value').replace(',', '')
    

    # Custom Statistics Search
    def get_custom_statistics_search(self, heading, row=None):
        return self._statistics_search(heading, row)


    # Statistics | Valuation measures
    def get_valuation_measures(self):
        return self._statistics_search('Valuation Measures')

    def get_market_cap(self):
        return self._statistics_search('Valuation Measures', 'Market Cap (intraday)')
    
    def get_enterprise_value(self):
        return self._statistics_search('Valuation Measures', 'Enterprise Value')

    def get_trailing_pe(self):
        return self._statistics_search('Valuation Measures', 'Trailing P/E')
    
    def get_forward_pe(self):
        return self._statistics_search('Valuation Measures', 'Forward P/E')
    
    def get_peg_ratio(self):
        return self._statistics_search('Valuation Measures', 'PEG Ratio (5 yr expected)')
    
    def get_price_per_sales(self):
        return self._statistics_search('Valuation Measures', 'Price/Sales')
    
    def get_price_per_book(self):
        return self._statistics_search('Valuation Measures', 'Price/Book')

    def get_enterprise_value_per_revenue(self):
        return self._statistics_search('Valuation Measures', 'Enterprise Value/Revenue')

    def get_enterprise_value_per_ebitda(self):
        return self._statistics_search('Valuation Measures', 'Enterprise Value/EBITDA')
    

    # Statistics | Financial highlights
    def get_financial_highlights(self):
        return self._statistics_search('Financial Highlights')

    def get_fiscal_year_ends(self):
        return self._statistics_search('Financial Highlights', 'Fiscal Year Ends')
    
    def get_most_recent_quarter(self):
        return self._statistics_search('Financial Highlights', 'Most Recent Quarter')
    
    def get_profit_margin(self):
        return self._statistics_search('Financial Highlights', 'Profit Margin')
    
    def get_operating_margin(self):
        return self._statistics_search('Financial Highlights', 'Operating Margin')
    
    def get_return_assets(self):
        return self._statistics_search('Financial Highlights', 'Return on Assets')
    
    def get_return_equity(self):
        return self._statistics_search('Financial Highlights', 'Return on Equity')
    
    def get_revenue(self):
        return self._statistics_search('Financial Highlights', 'Revenue')

    def get_revenue_per_share(self):
        return self._statistics_search('Financial Highlights', 'Revenue Per Share')
    
    def get_quarterly_revenue_growth(self):
        return self._statistics_search('Financial Highlights', 'Quarterly Revenue Growth')

    def get_gross_profit(self):
        return self._statistics_search('Financial Highlights', 'Gross Profit')
    
    def get_ebitda(self):
        return self._statistics_search('Financial Highlights', 'EBITDA')
    
    def get_net_income_avi_to_common(self):
        return self._statistics_search('Financial Highlights', 'Net Income Avi to Common')

    def get_diluted_eps(self):
        return self._statistics_search('Financial Highlights', 'Diluted EPS')
    
    def get_quarterly_earnings_growth(self):
        return self._statistics_search('Financial Highlights', 'Quarterly Earnings Growth')
    
    def get_total_cash(self):
        return self._statistics_search('Financial Highlights', 'Total Cash')
    
    def get_total_cash_per_share(self):
        return self._statistics_search('Financial Highlights', 'Total Cash Per Share')
    
    def get_total_debt(self):
        return self._statistics_search('Financial Highlights', 'Total Debt')
    
    def get_total_debt_per_equity(self):
        return self._statistics_search('Financial Highlights', 'Total Debt/Equity')
    
    def get_current_ratio(self):
        return self._statistics_search('Financial Highlights', 'Current Ratio')
    
    def get_book_value_per_share(self):
        return self._statistics_search('Financial Highlights', 'Book Value Per Share')
    
    def get_operating_cash_flow(self):
        return self._statistics_search('Financial Highlights', 'Operating Cash Flow')
    
    def get_levered_free_cash_flow(self):
        return self._statistics_search('Financial Highlights', 'Levered Free Cash Flow')
    

    # Statistics | Trading information
    def get_trading_information(self):
        return self._statistics_search('Trading Information')

    def get_beta(self):
        return self._statistics_search('Trading Information', 'Beta')
    
    def get_52_week_change(self):
        return self._statistics_search('Trading Information', '52-Week Change')
    
    def get_sp500_52_week_change(self):
        return self._statistics_search('Trading Information', 'S&P500 52-Week Change')
    
    def get_52_week_high(self):
        return self._statistics_search('Trading Information', '52 Week High')
    
    def get_52_week_low(self):
        return self._statistics_search('Trading Information', '52 Week Low')
    
    def get_50_day_average(self):
        return self._statistics_search('Trading Information', '50-Day Moving Average')
    
    def get_200_day_average(self):
        return self._statistics_search('Trading Information', '200-Day Moving Average')
    
    def get_avg_3_month_volume(self):
        return self._statistics_search('Trading Information', 'Avg Vol (3 month)')
    
    def get_avg_10_day_volume(self):
        return self._statistics_search('Trading Information', 'Avg Vol (10 day)')
    
    def get_shares_outstanding(self):
        return self._statistics_search('Trading Information', 'Shares Outstanding')
    
    def get_float(self):
        return self._statistics_search('Trading Information', 'Float')

    def get_percent_held_insiders(self):
        return self._statistics_search('Trading Information', '% Held by Insiders')
    
    def get_percent_held_institutions(self):
        return self._statistics_search('Trading Information', '% Held by Institutions')
    
    def get_shares_short(self):
        return self._statistics_search('Trading Information', 'Shares Short')

    def get_short_ratio(self):
        return self._statistics_search('Trading Information', 'Short Ratio')
    
    def get_short_percent_of_float(self):
        return self._statistics_search('Trading Information', 'Short % of Float')
    
    def get_shares_short_prior(self):
        return self._statistics_search('Trading Information', 'Shares Short (prior month)')
    
    def get_forward_dividend_rate(self):
        return self._statistics_search('Trading Information', 'Forward Annual Dividend Rate')
    
    def get_forward_dividend_yield(self):
        return self._statistics_search('Trading Information', 'Forward Annual Dividend Yield')
    
    def get_trailing_dividend_rate(self):
        return self._statistics_search('Trading Information', 'Trailing Annual Dividend Rate')
    
    def get_trailing_dividend_yield(self):
        return self._statistics_search('Trading Information', 'Trailing Annual Dividend Yield')
    
    def get_5_year_avg_dividend_yield(self):
        return self._statistics_search('Trading Information', '5 Year Average Dividend Yield')
    
    def get_payout_ratio(self):
        return self._statistics_search('Trading Information', 'Payout Ratio')
    
    def get_dividend_date(self):
        return self._statistics_search('Trading Information', 'Dividend Date')
    
    def get_exdividend_date(self):
        return self._statistics_search('Trading Information', 'Ex-Dividend Date')
    
    def get_last_split_factor(self):
        return self._statistics_search('Trading Information', 'Last Split Factor (new per old)')
    
    def get_last_split_date(self):
        return self._statistics_search('Trading Information', 'Last Split Date')
    

    # Profile | Company information
    def get_company_name(self):
        return self._search_soup(self.soup_profile, 'h3', 'data-reactid', '6')
    
    def get_company_address(self):
        return self._company_address(self.soup_profile, 'p', 'data-reactid', '8')
    
    def get_company_phone_number(self):
        return self._search_soup(self.soup_profile, 'a', 'data-reactid', '15')

    def get_company_website(self):
        return self._search_soup(self.soup_profile, 'a', 'target', '_blank')
    
    def get_sector(self):
        return self._search_soup(self.soup_profile, 'strong', 'data-reactid', '21')
    
    def get_industry(self):
        return self._search_soup(self.soup_profile, 'strong', 'data-reactid', '25')
    
    def get_number_of_full_time_employees(self):
        return self._search_soup(self.soup_profile, 'strong', 'data-reactid', '29')
    
    def get_key_executives(self):
        return self._key_executives(self.soup_profile, 'table', 'class', 'W(100%)')
 
    
    # Historical data
    def get_historical_day(self, date):
        return self._historical_data(date)
    
    def get_historical_days(self, from_date, to_date):
        return self._historical_data(from_date, to_date, 'days')
    
    def get_historical_range(self, from_date, to_date):
        return self._historical_data(from_date, to_date, 'range')
    

    # Analysts
    def get_analysts_earnings_estimate(self):
        return self._analysts_search('Earnings Estimate')
    
    def get_analysts_revenue_estimate(self):
        return self._analysts_search('Revenue Estimate')
    
    def get_analysts_earnings_history(self):
        return self._analysts_search('Earnings History')
    
    def get_analysts_eps_trend(self):
        return self._analysts_search('EPS Trend')
    
    def get_analysts_eps_revisions(self):
        return self._analysts_search('EPS Revisions')
    
    def get_analysts_growth_estimates(self):
        return self._analysts_search('Growth Estimates')


    # Refresh newest content
    def refresh(self):
        self.__init__(self.ticker)
