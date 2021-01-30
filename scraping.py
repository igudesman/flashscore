from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from time import sleep
from settings import leagues, URL, COEF
from signal import telegram_bot_sendtext
import os


class Bot():

    def __init__(self, url):

        chrome_options = webdriver.ChromeOptions()
        chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        self.driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), chrome_options=chrome_options)

        self.already_alerted_ids = []
        self.driver.implicitly_wait(10)
        self.url = url
        self.move_to_live_section()


    # move to the live section
    def move_to_live_section(self):

        self.driver.get(self.url)
        tabs = self.driver.find_elements_by_class_name('tabs__tab')
        for tab in tabs:
            if tab.text == 'LIVE':
                tab.click()
                print('Moved to LIVE section.')
                break


    def event_info(self, event_object):

        rows = event_object.find_elements_by_tag_name('div')
        event_stage = ''
        event_participant_home = ''
        event_participant_away = ''

        for row in rows:
            if row.get_attribute('class') == 'event__stage':
                event_stage = row.text
            if row.get_attribute('class') == 'event__participant event__participant--home':
                event_participant_home = row.text
            if row.get_attribute('class') == 'event__participant event__participant--away':
                event_participant_away = row.text

        id = event_object.get_attribute('id')
        id = id.split('_')[-1]
        event_url = 'https://www.flashscore.ru/match/{id}/#match-statistics;'.format(id=id)

        return {'id': id,
                'event_stage': event_stage,
                'event_participant_home': event_participant_home,
                'event_participant_away': event_participant_away,
                'event_url': event_url}


    def is_correct_league(self, league_object):

        league = league_object.find_element_by_class_name('event__titleBox')
        type = league.find_element_by_class_name('event__title--type').text
        name = league.find_element_by_class_name('event__title--name').text

        if type in leagues.keys():
            return True, {'type': type,
                          'name': name}

        return False, None


    def checking_loop(self, timeout):

        while True:
            # games_section = self.driver.find_element_by_class_name('sportName basketball')
            try:
                games_section = self.driver.find_element_by_xpath('//*[@id="live-table"]/div[2]/div/div')
            except:
                print('Access is denied. Trying again..')
                self.move_to_live_section()
                self.checking_loop(timeout)

            correct_league = False
            league_info = None
            block_id = 1

            while True:

                try:
                    event = self.driver.find_element_by_xpath('/html/body/div[5]/div[1]/div/div[1]/div[2]/div[4]/div[2]/div[2]/div/div/div[{}]'.format(block_id))
                except:
                    break

                try:
                    class_name = event.get_attribute('class')
                except:
                    break

                if 'event__header' in class_name:
                    correct_league, league_info = self.is_correct_league(event)
                    # print(league_info)
                    block_id += 1
                    continue

                if correct_league:
                    match_info = self.event_info(event)
                    bet = self.calculate_indicator(match_info)
                    match_info['league'] = league_info
                    # telegram_bot_sendtext(match_info, True)
                    if bet:
                        if match_info['id'] not in self.already_alerted_ids:
                            self.already_alerted_ids.append(match_info['id'])
                            telegram_bot_sendtext(match_info, False)

                block_id += 1

            # print('Iteration has gone.')
            sleep(timeout)


    def get_match_stats(self, content, quater):

        block_id = 1
        stat_rows = '/html/body/div[1]/div[1]/div[4]/div[12]/div[2]/div[4]/div[{q}]/div[{block_id}]'
        result = {}
        try:
            self.driver.find_element_by_xpath('//*[@id="statistics-{q}-statistic"]'.format(q=quater)).click()
        except:
            return result

        while True:
            try:
                stats = self.driver.find_element_by_xpath('//*[@id="tab-statistics-{q}-statistic"]/div[{block_id}]'.format(q=quater, block_id=block_id))
            except:
                break

            try:
                stats_class_name = stats.get_attribute('class')
            except:
                block_id += 1
                continue

            if (stats_class_name != 'statRow'):
                block_id += 1
                continue

            try:
                text_group = '//*[@id="tab-statistics-{q}-statistic"]/div[{block_id}]/div[1]/div[{text}]'
                print
                value_home = self.driver.find_element_by_xpath(text_group.format(q=quater, block_id=block_id, text=1)).text
                title = self.driver.find_element_by_xpath(text_group.format(q=quater, block_id=block_id, text=2)).text
                value_away = self.driver.find_element_by_xpath(text_group.format(q=quater, block_id=block_id, text=3)).text
                if title in content:
                    result[title] = [value_home, value_away]
            except:
                return {}

            block_id += 1

        return result


    def calculate_indicator(self, data):

        minute = 0
        quater = 0

        if ('Перерыв' in data['event_stage']):
            try:
                self.driver.find_element_by_xpath('//*[@id="g_3_{id}"]/div[11]'.format(id=data['id']))
            except:
                # print('Break.')
                return False
        elif ('Завершен' not in data['event_stage']) and ('Перенесен' not in data['event_stage']) and (data['event_stage'] != ''):
            try:
                quater = int(data['event_stage'][0])
                minute = int(data['event_stage'].splitlines()[1])

                if (quater != 3) or (minute < 9):
                    # print('Not 3-rd quarter.')
                    return False
            except:
                print('Something went wrong with event_stage: ', data['event_stage'])
                return False
        else:
            return False

        print('{0} - {1}'.format(data['event_participant_home'], data['event_participant_away']))

        # Switch to the new window and open URL B
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[1])
        self.driver.get(data['event_url'] + str(quater))
        #sleep(10)

        # getting quater's stats
        BET = ''
        for i in range(1, 4):

            rows = ['Бросков с игры %']
            stats = self.get_match_stats(rows, i)
            print('{i} quarter: {stats}'.format(i=i, stats=stats))
            if len(rows) != len(stats):
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                return False

            coef_home = float(stats[rows[0]][0].split('%')[0])
            coef_away = float(stats[rows[0]][1].split('%')[0])
            if (coef_home == 100.0) or (coef_away == 100.0):
                print('Stats = 100.0!')
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                return False

            if i == 3:
                if (coef_home >= 70.0) and (coef_away >= 70.0):
                    print('coefs are > 70.0!')
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return False
                elif coef_home >= 70:
                    BET = 'HOME'
                elif coef_away >= 70:
                    BET = 'AWAY'
                else:
                    print('coefs in 3rd quarter are < 70.0!')
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return False

        print(BET)
        # getting match odds
        odds = self.driver.find_elements_by_tag_name('tr')
        coefs = []

        for odd in odds:
            try:
                if odd.get_attribute('class') == 'odd':
                    spans = odd.find_elements_by_tag_name('span')
                    for span in spans:
                        try:
                            if 'odds-wrap' in span.get_attribute('class'):
                                coefs.append(float(span.text))
                        except:
                            continue
            except:
                continue

        print('COEFS: ', coefs)

        if len(coefs) != 2:
            print('Did not find coefs.')
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return False

        if BET == 'HOME':
            if coefs[0] < COEF:
                print('Home team coef does not match COEF!')
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                return False
        elif coefs[1] < COEF:
            print('Away team coef does not match COEF!')
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return False


        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])
        return True


def testing(bot):
    data = {
        'event_stage': '3 \n 10',
        'event_url': 'https://www.flashscore.ru/match/f5jCDOpC/#match-statistics;'
    }

    print(bot.calculate_indicator(data))


if __name__ == '__main__':

    bot = Bot(URL)
    bot.checking_loop(10)

    # testing(bot)
