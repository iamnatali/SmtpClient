import base64
import socket
import ssl
import re
from textwrap import wrap
import mimetypes
import os


class SmtpSender:
    def __init__(self):
        self.OK_init = True
        self.host_addr = 'smtp.mail.ru'
        self.port = 465
        self.error_dict = {
            '1': "The server accepted a command, but no actions have been taken. A confirmation message is required.",
            '2': "The task was completed successfully by the server without any mistakes.",
            '3': " The server understood the request, but further information is necessary for completing it.",
            '4': "A temporary failure occurred. If there are no changes while repeating the command, try again.",
            '5': "The server faces a critical error, and your command can't be handled."
        }
        with open('smtp_conf.txt', encoding='utf-8') as file:
            parts = file.readlines()
            self.targets = []
            self.theme = ""
            self.files = []
            length = len(parts)
            if length < 1 or length > 3:
                print("please fill smtp_conf.txt with data according to readme")
                self.OK_init = False
            else:
                self.targets = parts[0].split(" ")
                self.targets[len(self.targets)-1] = self.targets[len(self.targets)-1].replace('\n', '')
                if length >= 2:
                    self.theme = parts[1].replace('\n','')
                if length == 3:
                    self.files = parts[2].split(" ")
        with open('user_data.txt', encoding='utf-8') as file:
            parts = file.readlines()
            if len(parts) == 2:
                self.user_name = parts[0].replace('\n', '')
                self.password = parts[1]
            else:
                self.OK_init = False
                print("is is necesary to put e-mail and then password one per line in user_data.txt")

    def check_error(self, res_str):
        first = res_str[0]
        print(self.error_dict[first])
        if first != '4' and first != '5':
            print(res_str)
            return True
        return False

    def send(self):
        if self.OK_init:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
                try:
                    client.connect((self.host_addr, self.port))
                except socket.gaierror:
                    print("failed to connect.check your internet connection")
                else:
                    client = ssl.wrap_socket(client)
                    # аккуратно вычитать
                    byteStr = client.recv(1024)
                    success = self.check_error(byteStr.decode('utf-8'))
                    if success:
                        success = self.check_error(SmtpSender.request(client, 'EHLO natali'))
                        if success:
                            base64login = base64.b64encode(self.user_name.encode()).decode()
                            base64password = base64.b64encode(self.password.encode()).decode()
                            success = self.check_error(SmtpSender.request(client, 'AUTH LOGIN'))
                            if success:
                                success = self.check_error(SmtpSender.request(client, base64login))
                                if success:
                                    self.check_error(SmtpSender.request(client, base64password))
                                    for target_name in self.targets:
                                        self.session(client, target_name)

    def session(self, client, target_name):
        success = self.check_error(SmtpSender.request(client, 'MAIL FROM:' + self.user_name))
        if success:
            success = self.check_error(SmtpSender.request(client, "RCPT TO:" + target_name))
            if success:
                success =self.check_error(SmtpSender.request(client, 'DATA'))
                if success:
                    self.check_error(SmtpSender.request(client, self.create_message(target_name)))

    def create_message(self, target_name):
        bound = "bound123456789"
        head = self.create_head(target_name, bound)
        body = ""
        body += self.create_text_part(bound) + '\n'
        for file in self.files:
            body += self.create_part(bound, file)+'\n'
        body = body[0:len(body)-1]
        body += '--' + '\n'
        body += '.' + '\n'
        return head + body

    @staticmethod
    def request(socket, request):
        socket.send((request + '\n').encode())
        recv_data = socket.recv(65535).decode()
        return recv_data

    @staticmethod
    def add_dots(str):
        dot_pat = re.compile(r'\.+')
        mo = re.match(dot_pat, str)
        if mo:
            return str[0:len(str)-1]+"."
        else:
            return str

    @staticmethod
    def read_msg():
        with open('msg.txt', encoding='utf-8') as file:
            lines = file.readlines()
            changed_lines = map(SmtpSender.add_dots, lines)
            all_text = '\n'.join(changed_lines)
            return all_text

    @staticmethod
    def read_attach(file):
        path = os.path.join('resources',file)
        with open(path, 'rb') as f:
            all_file = f.read()
            return base64.b64encode(all_file).decode()

    @staticmethod
    def split_theme(theme):
        if len(theme) < 60:
            return "=?utf-8?B?" + base64.b64encode(theme.encode()).decode() + "?=" + '\n'
        else:
            res = ""
            toSplit = base64.b64encode(theme.encode()).decode()
            parts = wrap(toSplit, 60)
            last = parts.pop(len(parts)-1)
            for part in parts:
                res += "=?UTF-8?B?" + part + "?=" + '\n' + " "
            res += "=?UTF-8?B?" + last + "?=" + '\n'
            return res


    def create_head(self, target_name, bound):
        head = ""
        head += "From: " + self.user_name + "\n"
        head += "To: " + target_name + "\n"
        head += "Subject: " + SmtpSender.split_theme(self.theme)
        head += "MIME-Version: 1.0" + '\n'
        head += 'Content-Type: multipart/mixed; boundary="' + bound + '"' + '\n'
        head += "\n"
        return head

    def create_text_part(self, bound):
        body = ""
        body += "--" + bound + '\n'
        body += "Content-Transfer-Encoding: 7bit" + '\n'
        body += "Content-Type: text/plain" + '\n' + '\n'
        body += SmtpSender.read_msg() + '\n'
        body += "--" + bound
        return body

    def create_part(self, bound, file_name):
        t = mimetypes.guess_type(file_name)
        if not t[0]:
            print("unknown extention of file")
        body = ""
        body += 'Content-Disposition: attachment; filename="' + file_name + '"' + '\nContent-Transfer-Encoding: base64'
        type_string = '\nContent-Type: '+t[0]+'; name="' + file_name + '"' + '\n' + '\n'
        body += type_string
        body += SmtpSender.read_attach(file_name) + '\n'
        body += "--" + bound
        return body


if __name__ == '__main__':
    smtp = SmtpSender()
    smtp.send()
