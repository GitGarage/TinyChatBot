# Spam 2.6 Module
# odsum
# 04.06.18

import time
import re

import pinylib
from util import words

class Spam:

    def __init__(self, tinybot, conf):
        """
        Initialize the Spam class.

        :param tinybot: An instance of TinychatBot.
        :type tinybot: TinychatBot
        :param user: The User object to check.
        :type user: User
        :param conf: The config file.
        :type conf: config
        """
        self.tinybot = tinybot
        self.config = conf
        self.general = ["hey", "hi", "yes", "no", "yo", "sup", "hello", "cheers", "tokes"]
        self.msgs = {}

        self.recent_users = []
        self.recent_messages = []
        self.recent_times = [0, 0, 0, 0, 0]
        self.current_message = 0
        self.history = False
        for my_index in range(5):
            this_item = ['array%i' % my_index]
            self.recent_users.append(this_item)
            self.recent_messages.append(this_item)

        self.joind_time = 0
        self.joind_count = 0

        self.autoban_time = 0

        self.silent = False
        self.ban_time = 0
        self.lockdown = False

    def lockdown_onjoin(self, _user, t):

        if self.lockdown:
            return True

        if self.joind_time == 0:
            self.joind_time = t

        elif t - self.joind_time > 8:
            self.joind_count = 0
            self.joind_time = 0
            self.autoban_time = 0

        if self.joind_count > 3:
            self.autoban_time = t
            self.do_lockdown(0)
            return True

        self.joind_count += 1

        self.tinybot.console_write(pinylib.COLOR['cyan'], '[User] %s:%d joined the room. (%s)' % (
            _user.nick, _user.id, self.joind_count))

        return False

    def check_lockdown(self):

        tlaped = 240

        if self.autoban_time != 0:
            self.tinybot.console_write(pinylib.COLOR['red'],
                                       '[Security] Lockdown timer started: ' + format(self.autoban_time))
        else:
            self.autoban_time = time.time()
            tlaped = 3600
            self.tinybot.console_write(pinylib.COLOR['red'],
                                       '[Security] Lockdown manually called - 1hr')
        while True:
            if not self.lockdown:
                self.tinybot.console_write(pinylib.COLOR['red'], '[Security] Lockdown Mode Reset')
                break

            time.sleep(30)
            t = time.time()
            if self.autoban_time -t < tlaped:
                self.autoban_time = 0
                self.lockdown = False

                self.do_lockdown(1)

                self.tinybot.console_write(pinylib.COLOR['red'], '[Security] Lockdown Mode Reset')
                break

    def do_lockdown(self, soft):

        if not soft:
            password = self.tinybot.pinylib.string_util.create_random_string(5, 8)
        else:
            password = None

        if self.tinybot.is_client_owner:
            if self.lockdown:
                self.tinybot.privacy_.set_room_password(password)

                if not self.account_mode:
                    self.tinybot.privacy_.set_guest_mode()
                    self.account_mode = True

                self.lockdown = False

                self.tinybot.kick_pool[:] = []
                self.tinybot.ban_pool[:] = []

                time.sleep(2.0)
                self.tinybot.handle_msg(
                    '\n %s %s is open to the public again.' % (self.tinybot.boticon, self.tinybot.room_name))
            else:

                if not self.tinybot.privacy_.set_guest_mode():
                    self.account_mode = False
                    self.tinybot.privacy_.set_guest_mode()
                else:
                    self.account_mode = True

                self.lockdown = True

                if soft:
                    self.tinybot.handle_msg('\n %s Lockdown - no guests allowed.' % self.tinybot.boticon)
                else:
                    self.tinybot.handle_msg('\n %s Lockdown - tmp password is: %s' % (self.tinybot.boticon, password))

                self.tinybot.console_write(pinylib.COLOR['red'], '[Security] Lockdown started')
        else:

            if self.lockdown:
                if not self.config.B_ALLOW_GUESTS:
                    self.tinybot.do_guests(1)

                if not self.config.B_USE_KICK_AS_AUTOBAN:
                    self.tinybot.do_kick_as_ban(1)

                if self.silent and not self.config.B_VERBOSE:
                    self.tinybot.do_verbose(1)
                    self.silent = False

                self.tinybot.kick_pool[:] = []
                self.tinybot.ban_pool[:] = []

                self.lockdown = False
                self.joind_count = 0
                self.joind_time = 0
                self.autoban_time = 0
                self.check_lockdown()

                time.sleep(2.0)
                self.tinybot.handle_msg(
                    '\n %s %s is open to the public again.' % (self.tinybot.boticon, self.tinybot.room_name))
            else:

                if self.config.B_VERBOSE:
                    self.silent = True
                    self.tinybot.do_verbose(1)

                if self.config.B_ALLOW_GUESTS:
                    self.tinybot.do_guests(1)

                if self.config.B_USE_KICK_AS_AUTOBAN:
                    self.tinybot.do_kick_as_ban(1)

                self.lockdown = True
                time.sleep(2.0)
                self.tinybot.handle_msg('\n %s Lockdown - no guests allowed.' % self.tinybot.boticon)
                self.tinybot.console_write(pinylib.COLOR['red'], '[Security] Lockdown started')

    def check_msg(self, msg):

        spammer = False
        history = True if msg.startswith('!uptime') or msg.startswith('!clear') else False
        cleanse = False
        ban = False
        kick = False

        nazi = bool(re.search(r"musikkorps|musikorps|musicorps|mussikorps|musicorps|muusikorps|mussicorps|musikorpps|illien|musikorps|dreil", msg, re.IGNORECASE))

        if nazi:
            spammer = True
            ban = True

        if len(msg.splitlines()) > 8:
            cleanse = True
            spammer = True
            ban = True

        orig_length = len(msg)
        msg = words.removenonascii(msg)
        if orig_length > 20 and len(msg) < (orig_length/2):
            spammer = True
            ban = True

        if msg == '!history' and self.tinybot.active_user.user_level < 4:
            self.history = False if self.history else True
            history = True

        chat_words = msg.split(' ')

        chatr_user = self.tinybot.active_user.nick
        chatr_account = self.tinybot.active_user.account

        msg_time = int(time.time())

        if self.recent_users.count(chatr_user) > 1:
            pop_first = True
            first_time = 0
            for my_index in range(5):
                this_message = (self.current_message - my_index - 1) % 5
                if self.recent_users[this_message] == chatr_user:
                    if pop_first:
                        pop_first = False
                    else:
                        first_time = self.recent_times[this_message]
                        break
#            if (msg_time - first_time) < 15:
##               spammer = True
#               ban = True

        totalcopies = 0

        # each word reviewed and scored

        spamlevel = 0.1 # no such thing as no spam

        if len(msg) > 250:
            if self.tinybot.active_user.user_level > 3:
                spammer = True
                ban = True

        for word in chat_words:
            if word in self.general:
                spamlevel += 0.1 # word is a greeting
            else:
                if self.config.B_SPAMP:

                    if len(word) > 15:
                        spamlevel += 0.5 # word is longer than 15 characters

                    if len(word) > 100:
                        spammer = True
                        ban = True
                        # kenny

                    if not words.isword(word): # english only, comment out if needed.
                        spamlevel += 0.25  # for everyword that isn't english word

                    if word.isupper():
                        spamlevel += 0.25  # Uppercase word

                lword = word.lower()
                if self.tinybot.buddy_db.find_db_word_bans(lword):
                    ban = True
                    spammer = True

        if self.config.B_SPAMP:

            for m in self.msgs:

                if msg == m and m not in self.general:
                    totalcopies += 1
                    oldmsg = self.msgs[msg]
                    msgdiff = msg_time - oldmsg['ts']

                    if msgdiff < 4:
                        spamlevel += 0.35 # message repeated faster than 4 seconds

#                    if chatr_user is 'FAGBOS':  # user has wack nick
#                        ban = True
#                        spammer = True

                    if totalcopies > 0: # repeated message
                        spamlevel += 1.5

                        if oldmsg['nick'] == chatr_user:  # same nick as last spam
                            spamlevel += 1.0
                            spammer = True

                        if totalcopies > 1: # if copy exists more than 2 times
                            #self.autoban_time = time.time()
                            #self.do_lockdown(1)
                            ban = True

        mpkg = {'score': spamlevel, 'account': chatr_account, 'nick': chatr_user, 'msg': msg}

        self.msgs.update({'%s' % msg_time: mpkg})
        if len(self.msgs) > 12:  # store last 8 messages
            self.msgs.clear()

        if self.tinybot.active_user.user_level > 5:
            if spamlevel > 2.3:
                kick = True

            if spamlevel > 3.2:
                ban = True

        if not ban:
            if not kick:
                if not spammer:
                    if not history:
                        this_message = self.current_message % 5
                        self.recent_messages[this_message] = msg
                        self.recent_users[this_message] = chatr_user
                        self.recent_times[this_message] = msg_time
                        self.current_message += 1

        postext = ''

        if self.history:
            postext += 'Last %s message%s:' % (str(self.current_message if self.current_message < 5 else 5), ('' if self.current_message == 1 else 's'))
            if self.current_message < 5:
                for this_message in range(self.current_message):
                    postext += '\n\n%s: %s' % (self.recent_users[this_message], self.recent_messages[this_message])
            else:
                for message_index in range(5):
                    this_message = (self.current_message + message_index) % 5
                    postext += '\n\n%s: %s' % (self.recent_users[this_message], self.recent_messages[this_message])

        if ban:
            if self.tinybot.active_user.user_level > 3:
                if spammer and self.tinybot.active_user.user_level == 6:
                    self.tinybot.buddy_db.add_bad_account(self.tinybot.active_user.account)

                if self.lockdown:
                    self.tinybot.process_ban(self.tinybot.active_user.id)
                else:
                    self.tinybot.send_ban_msg(self.tinybot.active_user.id)

                postext = '%s %s was banned for spamming. %s' % (self.tinybot.boticon, self.tinybot.active_user.nick, postext)

                spamlevel = 666

        elif kick:
            if self.tinybot.active_user.user_level > 3:
                if self.lockdown:
                    self.tinybot.process_kick(self.tinybot.active_user.id)
                else:
                    self.tinybot.send_kick_msg(self.tinybot.active_user.id)

                self.tinybot.console_write(pinylib.COLOR['red'], 'postext:' + postext)
                postext = '%s %s was kicked for spamming. %s' % (self.tinybot.boticon, self.tinybot.active_user.nick, postext)

                spamlevel = 10
        if cleanse and self.history:
            while len(postext) > 0:
                time.sleep(0.7)
                send_part = ''
                all_words = postext.split(' ')
                while all_words and len(send_part + all_words[0]) + 1 < 500:
                    send_part += all_words.pop(0) + ' '
                self.tinybot.handle_msg(send_part)
                if all_words:
                    postext = ' '.join(all_words)
                else:
                    break

        return spamlevel
