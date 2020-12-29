import requests
from settings import TOKEN, chatID, message_form

def telegram_bot_sendtext(match_info):

    bot_message = message_form.format(league=match_info['league']['type'] + ': ' + match_info['league']['name'],
                                      team_1=match_info['event_participant_home'],
                                      team_2=match_info['event_participant_away'],
                                      time=match_info['event_stage'].splitlines()[0] + ' ' + match_info['event_stage'].splitlines()[1],
                                      url=match_info['event_url'])
    bot_token = TOKEN
    bot_chatID = chatID
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message

    response = requests.get(send_text)

    return response.json()
