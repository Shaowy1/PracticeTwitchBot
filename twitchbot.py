import socket
import types
import config
from collections import namedtuple

TEMPLATE_COMMANDS = {
    '!discord': 'Please join our {message.channel} Discord server, {message.user}',
    '!shout-out': 'Check out {message.text_args[0]}, they are a nice streamer',
}

Message = namedtuple(
    'Message',
    'prefix user channel irc_command irc_args text text_command text_args'
)

class Bot:
    def __init__(self):
        self.irc_server = 'irc.twitch.tv'
        self.irc_port = 6667
        self.oauth_token = config.OAUTH_TOKEN
        self.username = config.USERNAME
        self.channels = [config.USERNAME]

    def send_privmsg(self, channel, msg):
        self.send_command(f'PRIVMSG #{channel} :{msg}')

    def send_command(self, command):
        if 'PASS' not in command:
            print(f'< {command}')
        self.irc.send((command + '\r\n').encode())

    def connect(self):
        self.irc = socket.socket()
        self.irc.connect((self.irc_server, self.irc_port))
        self.send_command(f'PASS {self.oauth_token}')
        self.send_command(f'NICK {self.username}')
        for channel in self.channels:
            self.send_command(f'JOIN #{channel}')
            self.send_privmsg(channel, 'Hey there!')
        self.loop_for_messages()

    def get_user_from_prefix(self, prefix):
        domain = prefix.split('!')[0]
        if domain.endswith('.tmi.twitch.tv'):
            return domain.replace('.tmi.twitch.tv', '')
        if 'tmi.twitch.tv' not in domain:
            return domain
        return None

    def parse_message(self, received_msg):

        parts = received_msg.split(' ')

        prefix=None
        user=None
        channel=None
        irc_command=None
        irc_args=None
        text=None
        text_command=None
        text_args=None

        if parts[0].startswith(':'):
            prefix = parts[0][1:]
            user = self.get_user_from_prefix(prefix)
            parts = parts[1:]

        text_start = next(
            (idx for idx, part in enumerate(parts) if part.startswith(':')),
            None
        )

        if text_start is not None:
            text_parts = parts[text_start:]
            text_parts[0] = text_parts[0][1:]
            text = ' '.join(text_parts)
            text_command = text_parts[0]
            text_args = text_parts[1:]
            parts = parts[:text_start]

        irc_command = parts[0]
        irc_args = parts[1:]

        hash_start = next(
            (idx for idx, part in enumerate(irc_args) if part.startswith('#')),
            None
        )

        if hash_start is not None:
            channel = irc_args[hash_start][1:]

        message = Message(
            prefix=prefix,
            user=user,
            channel=channel,
            irc_command=irc_command,
            irc_args=irc_args,
            text=text,
            text_command=text_command,
            text_args=text_args
        )

        return message

    def handle_template_commands(self, message, text_command, template, text_args):

        try:
            text = template.format(**{'message': message})
            self.send_privmsg(message.channel, text)
        except:
            if text_command == '!shout-out' and len(text_args) == 0:
                self.send_privmsg(message.channel, 'Shout-out usage: !shout-out <name>')
            
            else:
                self.send_privmsg(message.channel, 'Something went wrong')

    def handle_message(self, received_msg):
        if len(received_msg) == 0:
            return
        message = self.parse_message(received_msg)
        print(f'> {message}')

        if message.irc_command == 'PING':
            self.send_command('PONG :tmi.twitch.tv')

        if message.irc_command == 'PRIVMSG':
            if message.text_command in TEMPLATE_COMMANDS:
                self.handle_template_commands(
                    message,
                    message.text_command,
                    TEMPLATE_COMMANDS[message.text_command],
                    message.text_args
                )

    def loop_for_messages(self):
        while True:
            received_msgs = self.irc.recv(2048).decode()
            for received_msg in received_msgs.split('\r\n'):
                self.handle_message(received_msg)

def main():
    bot = Bot()
    bot.connect()

if __name__ == "__main__":
    main()