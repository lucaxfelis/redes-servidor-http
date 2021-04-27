from socket import *
from urllib.parse import unquote_plus
import sys
import time
import threading
import os
import re

class WebServer(object):
    """
    Representa um servidor HTTP simples que utiliza protocolo de 
    comunicação TCP.
    """

    def __init__(self, host="localhost", port=8000):
        """
        Inicializa a classe com o host localhost, a porta 8000
        e o diretório ./web como padrão.
        """
        self.host = host
        self.port = port
        self.content_dir = './web'
        self.CONTENT_TYPES = {
            ".json": "text/json",
            ".html": "text/html",
            ".htm": "text/html",
            ".css": "text/css",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".mp4": "video/mp4",
            ".png": "image/png",
            ".gif": "image/gif",
            ".jpeg": "image/jpeg",
            ".jpg":  "image/jpeg",
            ".pdf": "application/pdf"
        }
        self.icons = {
            'green': "\033[37;42m # \033[00m",
            'error': "\n\033[37;41m ERRO: \033[00m",
            'yellow': "\n\033[37;43m # \033[00m"
            }

        bar = " # # # # # # "
        title = f"\n\033[30;47m{bar} SERVIDOR WEB HTTP {self.host}:{self.port} {bar}\033[00m"
        print(title)

    def start(self):
        """
        Cria e ativa um socket, e então publica o servidor. Se o
        diretório principal './web' não existir, ele será criado
        automaticamente.
        """

        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        
        if not os.path.isdir(self.content_dir):
            print(f"{self.icons['green']} Criando diretório principal './web'.\n")
            os.mkdir(self.content_dir)

        try:
            print(f"\n{self.icons['green']} Iniciando o servidor em {self.host}:{self.port}... ")
            self.socket.bind((self.host, self.port))
            print(f"{self.icons['green']} Servidor iniciado na porta {self.port}.")

        except Exception as e:
            print(f"{self.icons['error']} Não foi possível ligar a porta {self.port}!")
            self.shutdown()
            sys.exit(1)

        self._listen()

    def shutdown(self):
        """Desliga o servidor"""
        try:
            print(f"\r{self.icons['green']} Desligando o servidor.\n")
            self.socket.shutdown(SHUT_RDWR)

        except Exception as e:
            pass # caso o socket já esteja fechado

    def _generate_headers(
        self, 
        code, 
        content_type="text/html", 
        content_length="0"
        ):
        """Gera um cabeçalho de resposta HTTP.
        Parâmetros:
            - code: código de resposta a ser adicionado no
            cabeçalho de resposta.
            - content_type: tipo do conteúdo a ser devolvido pela
            resposta.
            - content_length: tamanho do conteúdo a ser devolvido pela
            pela resposta.
        Retorna:
            Um cabeçalho de resposta HTTP formatado de acordo com o
            código de resposta recebido como argumento.
        """
        status_codes = {
                200: 'OK', 
                400: "Bad Request", 
                404: "Not Found",
                501: "Not Implemented",
                505: "HTTP Version Not Supported"
            }
        
        time_now = time.strftime("%a, %d %b %Y %H:%M:%S %Z GMT", time.localtime())
        header = (
            f"HTTP/1.1 {code} {status_codes[code]}\r\n"
            f"Date: {time_now}\r\n"
            f"Server: Servidor-Redes-IF975\r\n"
            f"Content-type: {content_type}\r\n"
            f"Content-length: {content_length}\r\n\r\n"
        )

        return header

    def _listen(self):
        """Espera por alguma conexão na porta especificada"""
        self.socket.listen(5)
        while True:
            (client, address) = self.socket.accept()
            client_host, client_port = address
            client.settimeout(60)
            print(f"{self.icons['yellow']} Recebendo conexão de {client_host}:{client_port}")
            threading.Thread(target=self._handle_client, args=(client, address)).start()

    def _get_request_line(self, data):
        """
        Recebe os dados de uma requisição e retorna uma tupla
        contendo o método HTTP utilizado, o identificador do recurso
        e a versão do protoco utilizado.
        Parâmetros:
            data - dados do corpo da requisição
        Retorno:
            method - método utilizado pela requisição
            uri - o identificador do recurso
            version - versão utilizada do protocolo
        """

        line = data.split("\r\n")[0]
        (method, uri, version) = tuple(line.split(' '))
        return (method.upper(), unquote_plus(uri), version.upper())

    def _retrieve_error_page(self, socket, method, code):
        """
        Retorna uma página de erro pré-estabelecida pelo servidor   
        """
        file_path = {
            400: "./info_pages/bad_request.html",
            404: "./info_pages/not_found.html",
            501: "./info_pages/not_implemented.html",
            505: "./info_pages/http_version_not_supported.html"
        }
        content = ''
        with open(file_path[code], 'r', encoding='utf-8') as file:
            content += "\r\n".join(file.readlines())

        content_length = len(content)
        header = self._generate_headers(code, "text/html", content_length)

        if method == "GET":
            socket.send((header + content).encode())
            socket.close()
        elif method == "HEAD":
            socket.send((header).encode())
            socket.close()
        else:
            socket.send((header + content).encode())
            socket.close()

    def _retrieve_nav_page(self, socket, method, path, uri, target):
        """
        Retorna uma página de navegação que mostra os elementos contidos
        no diretório especificado

        Parâmetros:
            - socket: socket pelo qual será enviado a resposta
            - path: caminho do diretório  
        """

        content = ''

        def join_path(p, t):
            p = p.replace(self.content_dir, '')
            r = p + "/" + t
            return r.replace('//', '/')

        def back_path(p):
            p = p.replace(self.content_dir, '')
            return p.split('/')[0]

        with open("./info_pages/nav_page.html", 'r', encoding="utf-8") as file:
            content += "\r\n".join(file.readlines())

        print(path)   
        _, dirs, files = next(iter(os.walk(target)))
        list_items = (
            [(back_path(path), "..", "folder" ,) ]
            + [(join_path(path, d), d, "folder") for d in dirs]
            + [(join_path(path, f), f, "file") for f in files]
        )

        result = ""

        for url, name, img_type in list_items:
            result += f'<li><img src="./img/{img_type}.png"><a href="{url}">{name}</a></li>\n'

        args = {
            "{{dir}}": uri,
            "{{content}}": result
        }

        for k, v in args.items():
            content = content.replace(k, v)

        content_length = len(content)
        header = self._generate_headers(200, "text/html", content_length)

        if method == "GET":
            socket.send((header + content).encode())
        elif method == "HEAD":
            socket.send((header).encode())

    def _is_binary_file(self, path):
        """
        Retorna verdadeiro se o arquivo cujo caminho foi passado
        por parâmetro é um arquivo binário.
        """
        # Tenta abrir arquivo em modo de texto
        try:
            with open(file_name, 'tr') as check: 
                check.read()
                return False
        # Caso haja falha, arquivo é binário
        except:  
            return True

    def _extract_type(self, path):
        try:
            s = re.search(r".*(\.[a-z0-9]*)/{0,1}$", path)
            c_type = s.group(1)
            return self.CONTENT_TYPES[c_type] if c_type in self.CONTENT_TYPES else "text/plain"
        except:
            return "text/plain"

    def _retrieve_plain_file(self, socket, method, path, replaces=None):
        """Retorna um arquivo de texto plano."""
        content = ""
        with open(path, 'r', encoding="utf-8") as file:
            content += "\r\n".join(file.readlines())
        
        content_type = self._extract_type(path)
        content_length = len(content)
        
        header = self._generate_headers(200, content_type, content_length)

        if method == "GET":
            socket.send((header + content).encode())
        elif method == "HEAD":
            socket.send((header).encode())
    
    def _retrieve_binary_file(self, socket, method, path):
        """Retorna um arquivo binário"""
        CHUNK_SIZE = 32768
        content_type = self._extract_type(path)
        content_length = os.path.getsize(path)

        header = self._generate_headers(200, content_type, content_length)

        if method == "HEAD":
            socket.send(header.encode())
            socket.close()
            return
        elif method == "GET":
            socket.send(header.encode())

            with open(path, 'rb') as file:        
                while True:
                    readed = file.read(CHUNK_SIZE)

                    if readed: 
                        socket.send(readed)
                    else: 
                        break

    def _handle_client(self, client, address):
        """
        Main loop for handling connecting clients and serving files from content_dir
        Parameters:
            - client: socket client from accept()
            - address: socket address from accept()
        """
        PACKET_SIZE = 2048
        try:
            data = client.recv(PACKET_SIZE).decode() # Recieve data packet from client and decode

            # Se a requisição é vazia
            if not data: 
                self._retrieve_error_page(client, "GET", 400)
                

            # Realiza o processo na requisição
            try:
                method, uri, version = self._get_request_line(data)
                print(f"REQUEST: {method} {uri} {version}")
            # Se há erro de sintaxe, enviar a página 400 Bad Request
            except:
                self._retrieve_error_page(client, "GET", 400)
                
            # Se o método enviado não está implementado
            if not (method == "GET" or method == "HEAD"):
                # Envia página 501 Not Implemented
                self._retrieve_error_page(client, method, 501)
                
            # Buscar imagens da página de navegação
            elif uri.startswith("/img"):
                uri = "." + uri
                self._retrieve_binary_file(client, method, uri)
                
            # Requisição com erro de sintaxe
            elif not uri.startswith("/"):
                # Envia página 400 Bad Request
                self._retrieve_error_page(client, method, 400)
                
            # Requisição com versão de HTTP incompatível
            elif not (version == "HTTP/1.1" or version == "HTTP/1.0"):
                # Envia página 505 HTTP Version Not Supported
                self._retrieve_error_page(client, method, 505)
                        
            # Caso não haja erro na requisição
            else:
                      
                if uri != "/" and uri.endswith("/"):
                    uri = uri[0:-1]

                # Redireciona a requisição para o diretório principal
                target = self.content_dir + uri

                # Se o caminho existe
                if os.path.exists(target):

                    # Se o caminho é um diretório/pasta
                    if os.path.isdir(target):
                        dir_path = target
                        # Contém o arquivo index.html
                        if os.path.isfile(dir_path + "/index.html"):
                            self._retrieve_plain_file(
                                client, 
                                method, 
                                dir_path + "/index.html"
                                )
                            
                        
                        # Contém o arquivo index.htm
                        elif os.path.isfile(dir_path + "/index.htm"):
                            self._retrieve_plain_file(
                                client, 
                                method,
                                dir_path + "/index.htm"
                                )
                            
                        
                        # Exibe a página de navegação
                        else:
                            self._retrieve_nav_page(client, method, dir_path, uri, target)
                            
                    
                    # Se o caminho é um arquivo
                    elif os.path.isfile(target):

                        # Arquivo é binário
                        if self._is_binary_file(target):
                            self._retrieve_binary_file(client, method, target)
                        else:
                            self._retrive_plain_file(client, method, target)

                else:
                    self._retrieve_error_page(client, method, 404)

            client.close()
        except:
            client.close()