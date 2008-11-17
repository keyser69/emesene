import sys
import gtk
import time
import base64
import gobject

from core import Core
import dialog
import Window

import e3
from protocol import Action
from protocol import Config
from protocol import ConfigDir
from protocol import Logger

class Controller(object):
    '''class that handle the transition between states of the windows'''
    
    def __init__(self):
        '''class constructor'''
        self.window = None
        self.conversations = None
        self.core = Core()
        self.config = Config.Config()
        self.config_dir = ConfigDir.ConfigDir('emesene2')
        self.config.load(self.config_dir.join('config'))

        self.core.connect('login-succeed', self.on_login_succeed)
        self.core.connect('login-failed', self.on_login_failed)
        self.core.connect('contact-list-ready', self.on_contact_list_ready)
        self.core.connect('conv-first-action', self.on_new_conversation)
        self.core.connect('nick-change-succeed', self.on_nick_change_succeed)
        self.core.connect('message-change-succeed', 
            self.on_message_change_succeed)
        self.core.connect('status-change-succeed', 
            self.on_status_change_succeed)

    def on_close(self):
        '''called on close'''
        self.core.do_quit()
        self.window.hide()
        time.sleep(2)
        sys.exit(0)

    def on_login_succeed(self, core, args):
        '''callback called on login succeed'''
        self.window.clear()
        self.window.go_main(core.session, self.on_new_conversation,
            self.on_close)

    def on_login_failed(self, core, args):
        '''callback called on login failed'''
        dialog.error(args[0])
        self.window.content.set_sensitive(True)

    def on_contact_list_ready(self, core, args):
        '''callback called when the contact list is ready to be used'''
        self.window.content.contact_list.order_by_status = False
        self.window.content.contact_list.fill()
        self.window.content.panel.enabled = True

    def on_nick_change_succeed(self, core, args):
        '''callback called when the nick has been changed successfully'''
        nick = args[0]
        self.window.content.panel.nick.text = nick

    def on_status_change_succeed(self, core, args):
        '''callback called when the status has been changed successfully'''
        stat = args[0]
        self.window.content.panel.status.set_status(stat)

    def on_message_change_succeed(self, core, args):
        '''callback called when the message has been changed successfully'''
        message = args[0]
        self.window.content.panel.message.text = message

    def on_login_connect(self, account, remember_account, remember_password):
        '''called when the user press the connect button'''
        if self.config.l_remember_account is None:
            self.config.l_remember_account = []

        if self.config.l_remember_password is None:
            self.config.l_remember_password = []

        if remember_password:
            self.accounts[account.account] = account.password
            self.statuses[account.account] = account.status
            
            if account.account not in self.config.l_remember_account:
                self.config.l_remember_account.append(account.account)

            if account.account not in self.config.l_remember_password:
                self.config.l_remember_password.append(account.account)

        elif remember_account:
            self.accounts[account.account] = ''
            self.statuses[account.account] = account.status

            if account.account not in self.config.l_remember_account:
                self.config.l_remember_account.append(account.account)

        else:
            if account.account in self.config.l_remember_account:
                self.config.l_remember_account.remove(account.account)

            if account.account in self.config.l_remember_password:
                self.config.l_remember_password.remove(account.account)

            if account.account in self.accounts:
                del self.accounts[account.account]

            if account.account in self.statuses:
                del self.statuses[account.account]

        self._set_accounts()

        self.core.session.logger = Logger.LoggerProcess(
            self.config_dir.join(account.account, 'log'))
        self.core.session.logger.start()
        self.core.do_login(account.account, account.password, account.status)

    def on_new_conversation(self, core, args):
        '''callback called when the other user does an action that justify
        opeinig a conversation'''
        (cid, members) = args

        if self.conversations is None:
            window = Window.Window(self._on_conversation_window_close)
            window.set_default_size(640, 480)
            window.go_conversation(self.core.session)
            self.conversations = window.content
            window.show()

        (exists, conversation) = self.conversations.new_conversation(cid, 
            members)

        if exists:
            self.conversations.set_current_page(
                self.conversations.page_num(conversation))

        conversation.show_all()

        return (exists, conversation)

    def _on_conversation_window_close(self):
        '''method called when the conversation window is closed'''
        self.conversations = None

    def start(self, account=None, accounts=None):
        self.window = Window.Window(self.on_close)

        self.accounts = self._get_accounts()
        self.statuses = self._get_statuses()

        self.window.go_login(self.on_login_connect, account, self.accounts,
            self.config.l_remember_account, self.config.l_remember_password,
            self.statuses)

        self.window.show()

    def _get_accounts(self):
        '''return a dict containing all the accounts as keys and the passwords
        as values (empty strings if the passwords are not stored)
        '''

        accounts = self.config.l_accounts

        if accounts is None:
            return {}

        iterator = iter(accounts)

        return dict(zip(iterator, iterator))

    def _set_accounts(self):
        '''set the value of the accounts field on config from the dict of the
        class'''
        
        self.config.l_accounts = []
        self.config.l_statuses = []

        for (account, password) in self.accounts.iteritems():
            self.config.l_accounts.append(account)
            self.config.l_accounts.append(base64.b64encode(password))

        for (account, stat) in self.statuses.iteritems():
            self.config.l_statuses.append(account)
            self.config.l_statuses.append(stat)

        self.config.save(self.config_dir.join('config'))

    def _get_statuses(self):
        '''return a dict with the account as key and the status as value'''

        accounts = self.config.l_statuses

        if accounts is None:
            return {}

        iterator = iter(accounts)

        return dict(zip(iterator, iterator))


if __name__ == "__main__":
    gtk.gdk.threads_init()
    controller = Controller()
    controller.start()
    gtk.main()