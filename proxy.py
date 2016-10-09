#****************************************************
#                                                   *
#               HTTP PROXY                          *
#               Version: 1.0                        *
#               Author: Luu Gia Thuy                *
#       Modified Ian haywood 2016                                        *
#****************************************************

import os,sys,socket,select,urlparse,ssl,os.path, thread

#********* CONSTANT VARIABLES *********

# port the proxy runs on
PORT=8080
# path for the CA certificates and cache of fake certs for HTTPS sites.
# will be created if doesn't exist
CERTS_PATH=os.path.expanduser("~/certs")
 
BACKLOG = 50            # how many pending connections queue will hold
MAX_DATA_RECV = 999999  # max number of bytes we receive at once
BAN_HEADERS=['accept-encoding','connection']


# create, if required, fake SSL cert for this site
def create_cert(hostname):
    base = os.path.join(CERTS_PATH,hostname)
    cert = base+".pem"
    key = base+".key"
    if os.path.exists(cert):
        return (cert,key)
    if not os.path.exists(CERTS_PATH):
        os.mkdir(CERTS_PATH)
    olddir = os.getcwd()
    os.chdir(CERTS_PATH)
    if not os.path.exists(os.path.join(CERTS_PATH,"ca.pem")):
        # openssl voodoo to become our own CA
        # the CA certificate "ca.pem" will need to be imported into the browser for this to really work
        os.system("echo 1000 > serial")
        os.system("touch index.txt")
        os.system("openssl req -new -x509 -days 3650 -nodes -extensions v3_ca -subj '/C=AU/ST=Freedonia/L=Nowhere/O=THIS CERT IS FAKE/CN=localhost' -keyout ca.key -out ca.pem")
    # generate fake cert for this site.
    os.system("openssl req -new -nodes -keyout {0}.key -out {0}.req -subj '/C=AU/ST=Freedonia/L=Nowhere/O=THIS CERT IS FAKE/CN={0}'".format(hostname))
    os.system("openssl ca -batch -days 3650 -outdir {1} -cert {1}/ca.pem -config /etc/ssl/openssl.cnf -out {0}.pem1 -infiles {0}.req".format(hostname,CERTS_PATH))
    os.system("cat {0}.pem1 ca.pem > {0}.pem".format(hostname))
    os.chdir(olddir)
    return (cert,key)


#**************************************
#********* MAIN PROGRAM ***************
#**************************************
def main():

    print "Proxy Server Running on ",PORT

    try:
        # create a socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # associate the socket to host and port
        s.bind(("", PORT))

        # listenning
        s.listen(BACKLOG)
    
    except socket.error, (value, message):
        if s:
            s.close()
        print "Could not open socket:", message
        sys.exit(1)
    counter = 1
    # get the connection from client
    while 1:
        counter += 1
        conn, client_addr = s.accept()
        thread.start_new_thread(serve_conn,(conn, client_addr, counter))
    s.close()
#************** END MAIN PROGRAM ***************



CONNECT_REPLY=b"HTTP/1.1 200 Connectioln established\r\nProxy-Agent: proxy.py\r\n\r\n"

def filter_headers(headers):
    newheader = [headers[0]]
    for i in headers[1:]:
        fields = i.split(':', 1)
        field = fields[0].lower()
        if not field in BAN_HEADERS:
            newheader.append(i)
        if field == "connection":
            newheader.append("Connection: close")
    return "\r\n".join(newheader)  

def serve_conn(conn, client_addr, counter):

    # set up tracking files
    fd_client = open("%03d.client" % counter,"w")
    fd_server = open("%03d.server" % counter,"w")

    # get the request from browser
    request = conn.recv(MAX_DATA_RECV)
    # parse the first line
    lines = request.split('\r\n')
    # get url
    cmd = lines[0].split(' ')
    if len(cmd) != 3:
        print "PANIC: weird command: %r" % lines
    if len(cmd) < 2:
        return
    method = cmd[0]
    url = cmd[1]
    if method != 'CONNECT':
        dport = 80
        url = urlparse.urlparse(url)
        if url.scheme == 'https': dport = 443
        port = url.port or dport
        host = url.hostname
        request = filter_headers(lines)
        fd_client.write(request)
    else:
        host, port = url.split(':')
        print "CONNECT request %d host %s port %s" % (counter,host, port) 
        conn.send(CONNECT_REPLY)
    
    try:
        # create a socket to connect to the web server
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
        s.connect((host, int(port)))
        if method == 'CONNECT':
            # classic "man-in-the-middle" attack: establish SSL connection to both server and client, tricking
            # each that they are talking directly to the other one
            old_s = s
            s = ssl.wrap_socket(old_s)
            old_conn = conn
            cert, key = create_cert(host)
            conn = ssl.wrap_socket(conn,keyfile=key,certfile=cert,server_side=True)
            filtered = False
        else:
            filtered = True
            s.send(request)         # send request to webserver
        
        while 1:
            rfds, wfds, xfds = select.select([s,conn],[],[s,conn],20)
            if s in rfds:
                # receive data from web server
                data = s.recv(MAX_DATA_RECV)
                if (len(data) > 0):
                    # send to browser
                    conn.send(data)
                    fd_server.write(data)
                else:
                    break
            if conn in rfds:
                data = conn.recv(MAX_DATA_RECV)
                if (len (data) > 0):
                    if not filtered:
                        filtered = True
                        data = filter_headers(data.split("\r\n"))
                    s.send(data)
                    fd_client.write(data)
                else:
                    break
            if len(xfds) > 0:
                break
            if rfds == [] and xfds == []:
                # we timed out
                break
    except socket.error, (value, message):
        print "Peer Reset",lines,client_addr, value, message
    finally:
        try:
            s.close()
            conn.close()
            fd_server.close()
            fd_client.close()
        except: pass
#********** END PROXY_THREAD ***********
    
if __name__ == '__main__':
    main()


