#
# Серверное приложение для соединений
# Реализована проверка существующих логинов с учетом регистра
# Реализована история сообщений
# Пустые сообщения не сохраняем
# Историю сохраняем в dict (вдруг нужно будет выводить историю только по логину)
# Вычищаем пробелы перед рассылкой всем или сохранением
#
import asyncio
from asyncio import transports


class ServerProtocol(asyncio.Protocol):
    login: str = None
    server: 'Server'
    transport: transports.Transport

    def __init__(self, server: 'Server'):
        self.server = server

    def data_received(self, data: bytes):
        print(data)

        decoded = data.decode()
        if self.login is not None:
            self.send_message(decoded.strip())

        elif decoded.startswith("login:"):
            clean_login = decoded.replace("login:", "").replace("\r\n", "").strip()
            # Если логин пользователя прошел проверку - пускаем в чат
            if self.check_new_user(clean_login):
                self.send_history()
                self.register_new_user(clean_login)
        else:
            self.transport.write("Для входа в чат наберите login:ВашЛогин\n".encode())

    def connection_made(self, transport: transports.Transport):
        self.server.clients.append(self)
        self.transport = transport
        print("Пришел новый клиент")

    def connection_lost(self, exception):
        self.server.clients.remove(self)
        print("Клиент вышел")

    def check_new_user(self, user_login: str):
        # Проверим, что пользователей больше 1, иначе зачем проверять занятость логина
        if len(self.server.clients) > 1:
            # Проверка занятости логина у существующих пользователей
            if any(str(client.login).lower() == user_login.lower() for client in self.server.clients):
                self.transport.write(f"Логин {user_login} занят, попробуйте другой\n".encode())
                return False
            # Новый логин не занят
            else:
                return True
        # Число пользователей > 1
        else:
            return True

    def register_new_user(self, user_login: str):
        self.login = user_login
        self.transport.write(
            f"Привет, {self.login}!\n".encode()
        )

    def send_message(self, content: str):
        message = f"{self.login}: {content}\n"

        # Не сохраняем пустые сообщения
        if len(content) != 0:
            self.server.messages.append({"login": self.login, "text": content})

        # Рассылаем всем
        for user in self.server.clients:
            # Не дублируем сообщение самому себе
            if user != self:
                user.transport.write(message.encode())

    def send_history(self):
        for message in self.server.messages[-10:]:
            self.transport.write(f"{message['login']}: {message['text']}\n".encode())


class Server:
    clients: list

    def __init__(self):
        self.clients = []
        self.messages = []

    def build_protocol(self):
        return ServerProtocol(self)

    async def start(self):
        loop = asyncio.get_running_loop()

        coroutine = await loop.create_server(
            self.build_protocol,
            '127.0.0.1',
            8888
        )

        print("Сервер запущен ...")

        await coroutine.serve_forever()


process = Server()

try:
    asyncio.run(process.start())
except KeyboardInterrupt:
    print("Сервер остановлен вручную")