import requests
from settings import TOKEN, chatID, message_form
from datetime import datetime


def telegram_bot_sendtext(match_info, DEBUG=False):

    bot_token = TOKEN
    bot_chatID = chatID

    if DEBUG:
        bot_message = str(datetime.now())
        send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
        response = requests.get(send_text)
        return response.json()

    bot_message = message_form.format(league=match_info['league']['type'] + ': ' + match_info['league']['name'],
                                      team_1=match_info['event_participant_home'],
                                      team_2=match_info['event_participant_away'],
                                      time=match_info['event_stage'],
                                      url=match_info['event_url'])

    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
    response = requests.get(send_text)

    return response.json()
