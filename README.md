Web Proxy by Python
=====================

This is an extension of the Python web proxy by luagaathuy. It is extended in two main ways: all HTTP(S) traffic is logged to disk, plus
HTTPS sessions are decrypted using a MiTM attack. This allows the user to examine exactly what communciations happen between the browser and the server.
This is useful for automating HTTPS websites. It is not useful for spying on other peoples HTTPS connections as the browser must be explicitly configured to allow this. 

## Using the proxy

By default the proxy runs on port 8080. In firefox go to Preferences/Advanced/Network/Connection Settings/.
Select "Manual" proxy configuration, set the host to "127.0.0.1" and port to "8080"

## Saving files

The script saves each HTTP request and response to disk, the names are `XXX.client` (for the request), and `XXX.server`
(for the response), where XXX is an integer of the request in sequence. They are saved in the current directory.

## header modification

The proxy modifies outgoing headers in two ways: `Accept-Encoding` fields are stripped (to stop
servers compressing returned data), and `Connection: keep-alive` becomes `Connection: close`
(to force separate connections)

## Decrypting HTTPS

Setting this up is a bit of work. You need to have the `openssl` command available.

You probably need to edit /etc/ssl/openssl.cnf and set all the directories relating to CA work
to `$HOME/certs`. (This is the default, can be changed by editing the `CERTS_DIR` variable
in proxy.py)

The relevant section of my `/etc/ssl/openssl.cnf` looks like (my `$HOME` is `/home/ian`):

    [ CA_default ]

    dir		= /home/ian/certs		# Where everything is kept
    certs		= $dir/	# Where the issued certs are kept
    crl_dir		= $dir/crl		# Where the issued crl are kept
    database	= $dir/index.txt	# database index file.
    #unique_subject	= no			# Set to 'no' to allow creation of
					# several ctificates with same subject.
    new_certs_dir	= $dir		# default place for new certs.

    certificate	= $dir/ca.pem 	# The CA certificate
    serial		= $dir/serial 		# The current serial number
    crlnumber	= $dir/crlnumber	# the current crl number
					# must be commented out to leave a V1 CRL
    #crl		= $dir/crl.pem 		# The current CRL
    private_key	= $dir/ca.key # The private key
    RANDFILE	= $dir/.rand	# private random number file



When proxy.py tries to do HTTPS for the first time, it will create this directory and 
create the CA private key and certificate. The certificate file will be `$HOME/certs/ca.pem`.

Your browser will complain this CA is not recognised, and may refuse to connect you
to HTTPS websites at all. To fix this, you will need to install `$HOME/certs/ca.pem` as a Certificate
Authority. In Firefox: Preferences / Advanced / Certificates/ View Certificates / Authorites tab / Import...


##Usage
run
```
python proxy.py 
```
