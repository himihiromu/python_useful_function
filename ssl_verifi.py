import ssl
import socket
import OpenSSL
import certifi


addr = 'localhost'
cert_str = ssl.get_server_certificate((addr, 443))


def get_server_certificate(hostname):
    context = ssl.create_default_context()
    context.load_verify_locations(certifi.where())
    with socket.create_connection((hostname, 443)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as sslsock:
            der_cert = sslsock.getpeercert(True)
            return ssl.DER_cert_to_PEM_cert(der_cert)  

cert = get_server_certificate('www.google.com')
x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
print(x509)

cert = get_server_certificate(addr)
x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
print(x509)