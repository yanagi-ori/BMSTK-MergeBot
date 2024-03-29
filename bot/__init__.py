import cherrypy
import webhook
import logging

from bot import config
from bot.merger_bot import bot, db, decoder, encoder, key


class WebhookServer(object):
    @cherrypy.expose
    @cherrypy.tools.json_in()
    def index(self):
        # raw_body = cherrypy.request.body.read()
        raw_json = cherrypy.request.json  # получаем вебхук
        if raw_json['object_kind'] == 'merge_request':  # если вебхук вызван мержреквестом
            logging.debug(raw_json)

            webhook_object = webhook.Webhook(raw_json)
            action = raw_json['object_attributes'].get('action', None)  # действие

            for user in webhook_object.assignees_array:  # для каждого пользователя
                private_key = db.token.find_one({'idGitLab': encoder(user['username'])})
                # достаем ключ авторизации пользователя
                if private_key is None:
                    logging.error("Warning! No user was found to a merge request!")
                else:
                    if action is None:
                        continue
                    result = webhook_object.get_repo_compare(private_key)
                    for receiver in db.token.find({'idGitLab': encoder(user['username'])}):
                        if result:
                            # для каждого телеграм аккаунта, прикрепленного к этому юзеру
                            for j, file in enumerate(result['diffs']):
                                if action == 'open' or action == 'merged':
                                    webhook_object.send_open(receiver, file)
                                if action == 'reopen' and j < 1:
                                    webhook_object.send_reopen(receiver)
                                if action == 'update' and j < 1:
                                    webhook_object.send_update(receiver)
                                if action == 'close' and j < 1:
                                    webhook_object.send_close(receiver)
                                if action == 'none' and j < 1:
                                    webhook_object.send_new(receiver)
                                if (action == 'update' or action == 'close') \
                                        and len(result['diffs']) - 1 != 0 \
                                        and j >= 1:
                                    webhook_object.send_others(receiver, result)
                                    break  # прерываем вывод сообщений, чтобы не засорять чат
                        else:
                            webhook_object.send_undefined(receiver)

                        # отсылаем кнопочку со ссылкой на merge request
                        webhook_object.send_button(receiver)
