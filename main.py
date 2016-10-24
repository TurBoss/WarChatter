from PyQt4 import QtGui
import sys
import time
import socket
import ui
import re
import threading
import cgi
from PyQt4.QtCore import QThread, SIGNAL

class chat_thread(QThread):
    def __init__(self, username, password, server, channel, client_tag):

        print 'chat_thread.__init__()'

        QThread.__init__(self)
        self.username = str(username)
        self.password = str(password)
        self.server = str(server)
        self.channel = str(channel)
        self.client_tag = str(client_tag)
        self.login_attempts = 0
        self.end_flag = 0

    def __del__(self):

        print 'chat_thread.__del__()'

        self.wait()

    def pvpgn_login(self):

        print 'chat_thread.pvpgn_login()\n'

        while True:

            self.connection_status = 0

            try:
                self.buffer_size = 2048
                self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.s.connect((self.server, 6112))
                self.s.setblocking(0)
                self.s.settimeout(10)

                self.s.send("\r\n")

                self.s.send(self.username)
                self.s.send("\r\n")

                self.s.send(self.password)
                self.s.send("\r\n")

                total_data = [];
                data = ''
                while True:
                    data = self.s.recv(8192)
                    if 'Joining channel:' in data or 'Login failed.' in data:
                        total_data.append(data)
                        break
                    total_data.append(data)
                    if len(total_data) > 1:
                        # check if end_of_data was split
                        last_pair = total_data[-2] + total_data[-1]
                        if 'Joining channel:' in last_pair:
                            total_data[-2] = last_pair[:last_pair.find('Joining channel:')]
                            total_data.pop()
                            break
                data = ''.join(total_data)

                print 'WarChatter DEBUG: chat_thread.pvpgn_login() Output -----'
                print data
                print '--------------------------------------------------'

                if "failed" in data:
                    self.connection_status = 0
                    self.emit(SIGNAL('catch_status_msg(QString, QString)'), 'Login failed', 'red')
                    return

                elif "no bot" in data:
                    self.connection_status = 0
                    self.emit(SIGNAL('catch_status_msg(QString, QString)'), 'Server not supported', 'red')
                    return

                elif "Your unique name:" in data:
                    data_cleaned = re.findall('.+\n(Joining channel: .+)', data, flags=re.DOTALL)[0]
                    self.emit(SIGNAL('catch_textedit_chat(QString, QString)'), data_cleaned, 'white')
                    self.connection_status = 1
                    if self.channel:
                        if self.channel != "chat":
                            self.s.send("/join " + self.channel)
                            self.s.send("\r\n")
                            total_data = [];
                            data = ''
                            while True:
                                data = self.s.recv(8192)
                                if 'Joining channel:' in data or 'Login failed.' in data:
                                    total_data.append(data)
                                    break
                                total_data.append(data)
                                if len(total_data) > 1:
                                    # check if end_of_data was split
                                    last_pair = total_data[-2] + total_data[-1]
                                    if 'Joining channel:' in last_pair:
                                        total_data[-2] = last_pair[:last_pair.find('Joining channel:')]
                                        total_data.pop()
                                        break
                            data = ''.join(total_data)
                    self.emit(SIGNAL('catch_status_msg(QString, QString)'), 'Login success', 'green')
                    self.emit(SIGNAL('catch_textedit_chat(QString, QString)'), data, 'white')
                    return

                else:
                    self.connection_status = 0
                    self.emit(SIGNAL('catch_status_msg(QString, QString)'), 'Received invalid response', 'red')
                    break

            except Exception as e:
                print 'WarChatter Debug: chat_thread.pvpgn_login Socket Error -----'
                print e
                print '--------------------------------------------------------'
                self.emit(SIGNAL('catch_status_msg(QString, QString)'), 'No reply from server', 'red')
                self.connection_status = 0
                return

    def loop_chat_recv(self):
        if self.end_flag == 0:

            while True:
                try:

                    data = self.s.recv(8192)
                    if data:

                        self.emit(SIGNAL('catch_textedit_chat(QString, QString)'), data, 'white')
                        print '-----------'
                        print data
                        print '------------'
                        time.sleep(.1)
                except:
                    time.sleep(.1)
                    continue


    def run(self):
            print 'chat_thread.run()'
            self.pvpgn_login()
            if self.connection_status == 1:
                self.emit(SIGNAL('catch_login_success()'))
                self.loop_chat_recv()

class WarChatter(QtGui.QMainWindow, ui.Ui_MainWindow):
    def __init__(self):
        print 'WarChat.__init__()'
        # super allows us to access variables, methods etc in the ui.py file
        super(self.__class__, self).__init__()
        self.setupUi(self)  # This is defined in ui.py file automatically
        # It sets up layout and widgets that are defined
        self.button_login.clicked.connect(self.login)
        self.button_quit.clicked.connect(self.logout)
        self.button_send.clicked.connect(self.send_msg)
        self.button_whisper.clicked.connect(self.send_whisper)
        self.list_users.itemDoubleClicked.connect(self.open_profile)
        self.list_channels.itemClicked.connect(self.update_channel)
        self.list_channels.itemDoubleClicked.connect(self.open_channel)
        self.button_cancel_profile.clicked.connect(self.back_to_chat)
        self.button_cancel_channel.clicked.connect(self.back_to_chat)
        self.button_cancel_games.clicked.connect(self.back_to_chat)
        self.button_join.clicked.connect(self.open_games)
        self.button_channel.clicked.connect(self.open_channels)
        self.textedit_chat.setReadOnly(True)
        self.online_admins = []
        self.endflag = 0
        self.input_msg.returnPressed.connect(self.send_msg)
        self.input_username.returnPressed.connect(self.login)
        self.input_channel_2.returnPressed.connect(self.go_to_channel)
        self.button_ok_channel.clicked.connect(self.go_to_channel)
        self.input_password.returnPressed.connect(self.login)
        self.input_server.returnPressed.connect(self.login)
        self.input_channel.returnPressed.connect(self.login)
        self.input_client_tag.returnPressed.connect(self.login)
        # Gather and assign all the user input:
        self.username = ''
        self.password = ''
        self.server = ''
        self.print_admins = 0
        self.logged_on_admins = []
        self.channels = []
        self.games = []
        self.print_channels = 0
        self.first_time_check_channels = 0
        self.print_games = 0
        self.profile_name = ''
        self.profile_sex = ''
        self.profile_age = ''
        self.profile_location = ''
        self.profile_description = ''
        self.profile_stats = ''
        self.print_finger = 0
        self.print_stats = 0

    def update_channel(self):
        self.input_channel_2.setText(self.list_channels.currentItem().text())

    def go_to_channel(self):
        print 'go.to.channel()'

        channel = self.input_channel_2.text()
        if channel != '':
            print channel
            self.msg = '/join ' + channel
            if str(self.channel_name).lower() == str(channel).lower():
                self.stackedWidget.setCurrentIndex(1)

            else:
                self.msg = '/join ' + channel
                self.get_thread.s.send(str(self.msg))
                self.get_thread.s.send("\r\n")
                self.stackedWidget.setCurrentIndex(1)

    def open_channel(self):
        if str(self.channel_name).lower() == str(self.list_channels.currentItem().text()).lower():
            self.stackedWidget.setCurrentIndex(1)

        else:
            channel = self.list_channels.currentItem().text()
            self.msg = '/join ' + channel
            self.get_thread.s.send(str(self.msg))
            self.get_thread.s.send("\r\n")
            self.stackedWidget.setCurrentIndex(1)

    def open_games(self):
        self.msg = '/games ' + self.client_tag
        self.get_thread.s.send(str(self.msg))
        self.get_thread.s.send("\r\n")
        self.stackedWidget.setCurrentIndex(2)

    def open_channels(self):

        if self.first_time_check_channels == 0:
            self.msg = '/channels w2bn'
            self.get_thread.s.send(str(self.msg))
            self.get_thread.s.send("\r\n")
            self.first_time_check_channels = 1
        self.stackedWidget.setCurrentIndex(4)

    def open_profile(self):
        self.textedit_name.setText('')
        self.textedit_age.setText('')
        self.textedit_sex.setText('')
        self.textedit_location.setText('')
        self.textedit_description.setText('')
        self.textedit_stats.setText('')
        self.profile_name = ''
        self.profile_sex = ''
        self.profile_age = ''
        self.profile_location = ''
        self.profile_description = ''
        self.profile_stats = ''

        user = self.list_users.currentItem().text()
        print "/finger " + str(user) + ' ' + self.client_tag
        self.get_thread.s.send("/finger " + str(user) + " " + str(self.client_tag))
        self.get_thread.s.send("\r\n")
        time.sleep(.25)
        print "/stats " + str(user) + " " + self.client_tag
        self.get_thread.s.send("/stats " + str(user) + " " + str(self.client_tag))
        self.get_thread.s.send("\r\n")
        self.stackedWidget.setCurrentIndex(3)

    def back_to_chat(self):
        self.list_games.clear()
        self.stackedWidget.setCurrentIndex(1)

    def check_admins(self):

        if self.endflag == 0:
            self.get_thread.s.send("/admins")
            self.get_thread.s.send("\r\n")
            threading.Timer(60, self.check_admins).start()

        else:
            return

    def send_whisper(self):
        print 'WarChatter.send_whisper()'
        self.username = self.input_username.text()
        self.msg = str(self.input_msg.text())
        self.whisper_user = self.list_users.currentItem().text()
        self.msg = '/m ' + str(self.whisper_user) + ' ' + self.msg
        self.input_msg.setText('')

        if re.findall('(^https?)://(.+?)\..+', self.msg.lower()):

            self.get_thread.s.send(self.msg)
            self.get_thread.s.send("\r\n")

            word_list = []
            msg_words = self.msg.split()
            for word in msg_words:
                word_lower = word.lower()
                if re.findall('^https?://.+?\..+', word_lower):
                    link_parts = re.findall('^(https?://.+)', word_lower)
                    link = link_parts[0]
                    link = '<a href="' + link + '">' + link + '</a>'
                    word_list.append(link)
                else:
                    word_list.append(word)

            self.msg = ' '.join(word_list)

            print self.msg

            msg = '<span style="color: #00ffff;">&lt;' + self.username + '&gt;</span><span style="color: white;" > ' + self.msg + '</span>'



        else:
            self.get_thread.s.send(self.msg)
            self.get_thread.s.send("\r\n")
            msg = '<span style="color: #00ffff;">&lt;' + self.username + '&gt;</span><span style="color: white;" > ' + self.msg + '</span>'



    def send_msg(self):
        print 'WarChatter.send_msg()'
        # Gather and assign all the user input:
        self.username = self.input_username.text()
        self.msg = str(self.input_msg.text())

        self.input_msg.setText('')

        if re.findall('^/channels$', self.msg):
            self.print_channels = 1
            self.msg = self.msg + ' ' + self.client_tag
            print self.msg
            self.get_thread.s.send(str(self.msg))
            self.get_thread.s.send("\r\n")

        elif re.findall('^/join', self.msg):
            self.get_thread.s.send(self.msg)
            self.get_thread.s.send("\r\n")

        elif re.findall('^/finger', self.msg):

            print 'set finger to 1'
            self.print_finger = 1
            self.msg = self.msg + ' ' + str(self.client_tag)
            print self.msg
            self.get_thread.s.send(self.msg)
            self.get_thread.s.send("\r\n")

        elif re.findall('^/admins$', self.msg):
            self.print_admins = 1
            self.get_thread.s.send(self.msg)
            self.get_thread.s.send("\r\n")

        elif re.findall('^/stats$', self.msg):
            self.msg = self.msg + ' ' + self.username + ' ' + self.client_tag
            print self.msg
            self.get_thread.s.send(str(self.msg))
            self.get_thread.s.send("\r\n")

        elif re.findall('^/ladderinfo (.+?)$', self.msg):
            self.msg = self.msg + ' ' + self.client_tag
            print self.msg
            self.get_thread.s.send(str(self.msg))
            self.get_thread.s.send("\r\n")

        elif re.findall('^/games$', self.msg):
            self.msg = self.msg + ' ' + self.client_tag
            self.print_games = 1
            print self.msg
            self.get_thread.s.send(str(self.msg))
            self.get_thread.s.send("\r\n")

        elif re.findall('^/stats (.+?)$', self.msg):
            self.print_stats = 1
            self.msg = self.msg + ' ' + self.client_tag
            print self.msg
            self.get_thread.s.send(str(self.msg))
            self.get_thread.s.send("\r\n")

        elif re.findall('^/', self.msg):
            self.get_thread.s.send(self.msg)
            self.get_thread.s.send("\r\n")

        elif re.findall('(https?)://(.+?)\..+', self.msg.lower()):

            self.get_thread.s.send(self.msg)
            self.get_thread.s.send("\r\n")

            word_list = []
            msg_words = self.msg.split()
            for word in msg_words:
                word_lower = word.lower()
                if re.findall('^https?://.+?\..+', word_lower):
                    link_parts = re.findall('^(https?://.+)', word_lower)
                    link = link_parts[0]
                    link = '<a href="' + link + '">' + link + '</a>'
                    word_list.append(link)
                else:
                    word_list.append(word)

            self.msg = ' '.join(word_list)

            print self.msg

            msg = '<span style="color: #00ffff;">&lt;' + self.username + '&gt;</span><span style="color: white;" > ' + self.msg + '</span>'
            self.catch_textedit_chat_2(msg, 'white')


        else:
            self.get_thread.s.send(self.msg)
            self.get_thread.s.send("\r\n")
            msg = '<span style="color: #00ffff;">&lt;' + self.username + '&gt;</span><span style="color: white;" > ' + self.msg + '</span>'
            self.catch_textedit_chat_2(msg, 'white')

    def logout(self):
        threading.Timer(3, self.check_admins).cancel()
        self.end_flag = 1

        self.get_thread.s.send("/logout")
        self.get_thread.s.send("\r\n")
        self.get_thread.s.close()


        self.textedit_chat.setText('')

        self.textedit_chat.setHtml(ui._translate("MainWindow",
                                              "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
                                              "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
                                              "p, li { white-space: pre-wrap; }\n"
                                              "</style></head><body style=\" font-family:\'Droid Sans\'; font-size:12pt; font-weight:400; font-style:normal;\" bgcolor=\"#000000\">\n"
                                              "<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>",
                                              None))
        self.list_users.clear()
        self.logged_on_admins = []
        self.label_status_msg.setText("")
        self.stackedWidget.setCurrentIndex(0)


    def login(self):
        print 'WarChat.login()'

        # Gather and assign all the user input:
        self.username = self.input_username.text()
        self.password = self.input_password.text()
        self.server = self.input_server.text()
        self.channel = self.input_channel.text()
        self.client_tag = self.input_client_tag.text()
        # Validate user input/check for missing params
        if not self.username or not self.password:
            self.label_status_msg.setText("Username/Password missing")
            self.label_status_msg.setStyleSheet('color: red')
            return

        # Create chat_thread object
        self.get_thread = chat_thread(self.username, self.password, self.server, self.channel, self.client_tag)

        # Setup signals to listen for and connect them to functions
        self.connect(self.get_thread, SIGNAL("catch_status_msg(QString, QString)"), self.catch_status_msg)
        self.connect(self.get_thread, SIGNAL("catch_textedit_chat(QString, QString)"), self.catch_textedit_chat)
        self.connect(self.get_thread, SIGNAL("catch_login_success()"), self.catch_login_success)

        # Start chat_thread
        self.get_thread.start()

        self.label_status_msg.setText("Connecting...")
        self.label_status_msg.setStyleSheet('color: light gray')

    def catch_login_success(self):
        threading.Timer(3, self.check_admins).start()
        self.stackedWidget.setCurrentIndex(1)

    def catch_status_msg(self, msg, color):

        print 'WarChat.catch_status_msg()'

        self.label_status_msg.setText(msg)
        self.label_status_msg.setStyleSheet('color: ' + color)

    def catch_textedit_chat_2(self, msg, color):
        self.textedit_chat.append(str(msg).decode('string_escape'))

    def catch_textedit_chat(self, msg, color):

        print 'WarChat.catch_textedit_chat()'

        # This is where all the chatroom data styling and filtering takes place
        msg = str(msg)

        if re.findall('^ -----------name----------- users ----admin/operator----', msg):
            self.list_channels.clear()
            self.channels = []
            msg_2 = msg.splitlines()
            for line in msg_2:

                if re.findall('^ (.+) .?.?.?.?.?.?.?.?.? -', line):

                    self.channels.append(re.findall('^ (.+) .?.?.?.?.?.?.?.?.? -', line)[0].strip())

                    if self.print_channels == 1:
                        line = '<span style="color: #ffff00;">' + line + '</span>'
                        self.textedit_chat.append(str(line).decode('string_escape'))

            self.channels.pop(0)
            for channel in self.channels:
                self.list_channels.addItem(channel)
            print self.channels
            self.input_channel_2.setText(self.channels[0])

            return

        if re.findall('^ ------name------ p -status- --------type--------- count', msg):
            self.list_games.clear()
            self.games = []

            msg_2 = msg.splitlines()

            for line in msg_2:


                if re.findall('^\s(.+?)\s.\s', line):

                    if 'open' in line:
                        self.games.append(re.findall('^\s(.+?)\s.\s', line)[0].strip())
                        game = re.findall('^\s(.+?)\s.\s', line)[0].strip()
                        print game

                    if self.print_games == 1:
                        line = '<span style="color: #ffff00;">' + line + '</span>'
                        self.textedit_chat.append(str(line).decode('string_escape'))

            for game in self.games:
                self.list_games.addItem(game)
            print self.games
            self.print_games = 0
            return

        if re.findall('^Created:', msg):
            list_profile_description = []
            msg_2 = msg.splitlines()

            for line in msg_2:

                if re.findall('^Created: (.+?)', line):

                    if self.print_finger == 1:
                        line = '<span style="color: #ffff00;">' + line + '</span>'
                        self.textedit_chat.append(line.decode('string_escape'))

                elif re.findall('^Clan ?: (.+) Rank: (.+?)', line):

                    if self.print_finger == 1:
                        line = '<span style="color: #ffff00;">' + line + '</span>'
                        self.textedit_chat.append(line.decode('string_escape'))
                elif re.findall('^Client: ', line):
                    pass
                elif re.findall('^On since ', line):
                    pass
                elif re.findall('^Idle ', line):
                    pass
                elif re.findall('^Location: (.+?) Age:', line):

                    self.profile_location = re.findall('^Location: (.+?) Age:', line)[0].decode('string_escape')

                    if re.findall('^Location: .+? Age: (.+)', line):
                        self.profile_age = re.findall('^Location: .+? Age: (.+)', line)[0].decode('string_escape')
                        self.textedit_age.setText(self.profile_age)
                    list_profile_location = []

                    if re.findall('https?://.+?\.', self.profile_location.lower()):

                        msg_words = self.profile_location.split()
                        word_list = []
                        for word in msg_words:
                            word_lower = word.lower()
                            if re.findall('^https?://.+?\..+', word_lower):
                                link_parts = re.findall('^(https?://.+)', word_lower)
                                link = link_parts[0]
                                link = '<a href="' + link + '">' + link + '</a>'
                                word_list.append(link)
                            else:
                                word_list.append(word)
                        word_list = ' '.join(word_list)
                        word_list = '<span>' + word_list + '</span>'
                        list_profile_location.append(word_list)


                    else:
                        line = '<span>' + cgi.escape(line) + '</span>'
                        list_profile_location.append(self.profile_location)

                    self.profile_location = '<br>'.join(list_profile_location).decode('string_escape')
                    print self.profile_location
                    self.textedit_location.setText(self.profile_location)

                    if self.print_finger == 1:

                        print 'yes print finger !!!'
                        line = '<span style="color: #ffff00;">' + line + '</span>'
                        self.textedit_chat.append(line.decode('string_escape'))

                else:
                    if re.findall('https?://.+?\.', line.lower()):

                        msg_words = line.split()
                        word_list = []
                        for word in msg_words:
                            word_lower = word.lower()
                            if re.findall('^https?://.+?\..+', word_lower):
                                link_parts = re.findall('^(https?://.+)', word_lower)
                                link = link_parts[0]
                                link = '<a href="' + link + '">' + link + '</a>'
                                word_list.append(link)
                            else:
                                word_list.append(cgi.escape(word))
                        word_list = ' '.join(word_list)
                        word_list = '<span>' + word_list + '</span>'
                        list_profile_description.append(word_list)


                    else:
                        line = '<span>' + cgi.escape(line) + '</span>'
                        list_profile_description.append(line)

                    if self.print_finger == 1:

                        print 'yes print finger !!!'
                        line = '<span style="color: #ffff00;">' + line + '</span>'
                        self.textedit_chat.append(line.decode('string_escape'))
                        self.print_finger = 0



                    self.profile_description = '<br>'.join(list_profile_description).decode('string_escape')
                    print self.profile_description
                    self.textedit_description.setText(self.profile_description)

            return

        msg = msg.splitlines()
        for line in msg:

            self.link_flag = 0

            if re.findall('https?://.+?\.', line.lower()):

                msg_words = line.split()
                word_list = []
                for word in msg_words:
                    word_lower = word.lower()
                    if re.findall('^https?://.+?\..+', word_lower):
                        link_parts = re.findall('^(https?://.+)', word_lower)
                        link = link_parts[0]
                        link = '<a href="' + link + '">' + link + '</a>'
                        word_list.append(link)
                    else:
                        word_list.append(word)

                self.line_w_links = ' '.join(word_list)
                self.link_flag = 1


            if re.findall('^Joining channel: "(.+)"$', line):
                self.list_users.clear()
                self.channel_name = re.findall('^Joining channel: "(.+)"$', line)[0]
                print re.findall('^Joining channel: (.+)$', line)

                if self.link_flag == 1:
                    line = '<span style="color: #00ef00;">' + self.line_w_links + '</span>'
                    self.textedit_chat.append(line)

                else:
                    line = '<span style="color: #00ef00;">' + line + '</span>'
                    self.textedit_chat.append(line)

            elif re.findall('^Login: (.+) #.+? Sex:', line):
                self.profile_name = re.findall('^Login: (.+) #.+? Sex:', line)[0].decode('string_escape')
                self.textedit_name.setText(self.profile_name)
                if re.findall('^Login: (.+) #.+? Sex: (.+)', line):
                    self.profile_sex = re.findall('^Login: (.+) #.+? Sex: (.+)', line)[0][1].decode('string_escape')
                    self.textedit_sex.setText(self.profile_sex)
                if self.print_finger == 1:
                    print 'yes print finger !!!'
                    line = '<span style="color: #ffff00;">' + line + '</span>'
                    self.textedit_chat.append(line.decode('string_escape'))


            elif re.findall('^Currently logged on Administrators:', line):
                try:
                    self.logged_on_admins = re.findall('^Currently logged on Administrators: (.+)', line)[0]
                    self.logged_on_admins = self.logged_on_admins.split()
                except:
                    pass


                if self.print_admins == 1:
                    line = '<span style="color: #ffff00;">' + line + '</span>'
                    self.textedit_chat.append(line.decode('string_escape'))
                    self.print_admins = 0

            elif re.findall('\'s record:$', line):
                    if self.print_stats == 1:
                        line = '<span style="color: #ffff00;">' + line + '</span>'
                        self.textedit_chat.append(line.decode('string_escape'))

            elif re.findall('^Normal games:', line):
                    if self.print_stats == 1:
                        line = '<span style="color: #ffff00;">' + line + '</span>'
                        self.textedit_chat.append(line.decode('string_escape'))

            elif re.findall('^Ladder games:', line):
                    if self.print_stats == 1:
                        line = '<span style="color: #ffff00;">' + line + '</span>'
                        self.textedit_chat.append(line.decode('string_escape'))

            elif re.findall('^IronMan games:', line):
                    if self.print_stats == 1:
                        line = '<span style="color: #ffff00;">' + line + '</span>'
                        self.textedit_chat.append(line.decode('string_escape'))
                        self.print_stats = 0

            elif re.findall('^\[(.+)\]$', line):
                user_status_msg = re.findall('^\[(.+)\]$', line)


                if 'is here' in user_status_msg[0]:
                    user = re.findall('^\[(.+) is here\]$', line)
                    self.list_users.addItem(user[0])
                    self.update_list_users()

                elif 'enters' in user_status_msg[0]:
                    user = re.findall('^\[(.+) enters\]$', line)
                    self.list_users.addItem(user[0])
                    self.update_list_users()

                elif 'quit' in user_status_msg[0]:
                    user = re.findall('^\[(.+) quit\]$', line)
                    self.remove_from_user_list(user)
                    self.update_list_users()

                elif 'leaves' in user_status_msg[0]:
                    user = re.findall('^\[(.+) leaves\]$', line)
                    self.remove_from_user_list(user)
                    self.update_list_users()

                elif 'kicked' in user_status_msg[0]:
                    user = re.findall('^\[(.+) has been kicked\]$', line)
                    self.remove_from_user_list(user)
                    self.update_list_users()

                elif 'banned' in user_status_msg[0]:
                    user = re.findall('^\[(.+) has been banned\]$', line)
                    self.remove_from_user_list(user)
                    self.update_list_users()

            elif re.findall('^Current channels of type', line):
                if self.print_channels == 1:
                    line = '<span style="color: #ffff00;">' + line + '</span>'
                    self.textedit_chat.append(str(line).decode('string_escape'))

            elif re.findall('^Current games of type', line):
                if self.print_games == 1:
                    line = '<span style="color: #ffff00;">' + line + '</span>'
                    self.textedit_chat.append(str(line).decode('string_escape'))

            elif re.findall('^ERROR: ', line):
                line = line.replace("ERROR: ", "", 1)
                if self.link_flag == 1:
                    line = '<span style="color: #ff0000;">' + self.line_w_links + '</span>'
                    self.textedit_chat.append(str(line).decode('string_escape'))
                else:
                    line = '<span style="color: #ff0000;">' + line + '</span>'
                    self.textedit_chat.append(str(line).decode('string_escape'))

            elif re.findall('^Connection closed.$', line):

                pass

            elif re.findall('^Connection closed.$', line):
                pass

            elif re.findall('^<from (.+?)>', line):
                username = re.findall('^<from (.+?)> ', line)[0]
                if self.link_flag == 1:

                    line = self.line_w_links.replace("from ", "From:", 1)
                    line = '<span style="color: #ffff00;">&lt;From: ' + username + '&gt;</span><span style="color: gray;" > ' + line + '</span>'
                    self.textedit_chat.append(str(line).decode('string_escape'))

                else:

                    line = line.replace("from ", "From:", 1)
                    line = '<span style="color: #ffff00;">&lt;From: ' + username + '&gt;</span><span style="color: gray;" > ' + line + '</span>'
                    self.textedit_chat.append(str(line).decode('string_escape'))

            elif re.findall('^<to (.+?)>', line):
                username = re.findall('^<to (.+?)> ', line)[0]
                if self.link_flag == 1:

                    line = self.line_w_links.replace("to ", "To:", 1)
                    line = '<span style="color: #00ffff;">&lt;To: ' + username + '&gt;</span><span style="color: gray;" > ' + line + '</span>'
                    self.textedit_chat.append(str(line).decode('string_escape'))

                else:

                    line = line.replace("to ", "To:", 1)
                    line = '<span style="color: #00ffff;">&lt;To: ' + username + '&gt;</span><span style="color: gray;" > ' + line + '</span>'
                    self.textedit_chat.append(str(line).decode('string_escape'))

            elif re.findall('^<(.+?)> ', line):
                username = re.findall('^<(.+?)> ', line)[0]
                if username in self.logged_on_admins:

                    if self.link_flag == 1:

                        line = '<span style="color: #00ffff;">&lt;' + username + '&gt;</span><span style="color: #00ffff;" > ' + self.line_w_links + '</span>'
                        self.textedit_chat.append(str(line).decode('string_escape'))

                    else:

                        line = '<span style="color: #00ffff;">&lt;' + username + '&gt;</span><span style="color: #00ffff;" > ' + line + '</span>'
                        self.textedit_chat.append(str(line).decode('string_escape'))
                else:

                    if self.link_flag == 1:
                        line = '<span style="color: #ffff00;">&lt;' + username + '&gt;</span><span style="color: white;" > ' + self.line_w_links + '</span>'
                        self.textedit_chat.append(str(line).decode('string_escape'))

                    else:
                        line = '<span style="color: #ffff00;">&lt;' + username + '&gt;</span><span style="color: white;" > ' + line + '</span>'
                        self.textedit_chat.append(str(line).decode('string_escape'))

            else:
                if self.link_flag == 1:
                    self.textedit_chat.append('<span style="color: #ffff00;">' + str(self.line_w_links).decode('string_escape') + '</span>')

                else:
                    self.textedit_chat.append('<span style="color: #ffff00;">' + str(line).decode('string_escape') + '</span>')


    def remove_from_user_list(self, user):
        user_count = self.list_users.count()
        for i in range(user_count):
            print self.list_users.item(i).text()
            if user[0] == self.list_users.item(i).text():
                self.list_users.takeItem(i)
                break

    def update_list_users(self):

        self.channel_user_count = self.list_users.count()
        self.label_channel.setText(self.channel_name + ' (' + str(self.channel_user_count) + ')')


def main():
    app = QtGui.QApplication(sys.argv)  # A new instance of QApplication
    form = WarChatter()  # Set the form to be WarChatter (ui.py)
    form.show()  # Show the form
    app.exec_()  # Execute the app


if __name__ == '__main__':  # if running this file directly and not importing it
    main()  # run the main function