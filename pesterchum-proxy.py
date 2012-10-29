#!/usr/bin/env python3
import logging
import traceback
import socket
import select
import re
import threading
import optparse
import sys

parser = optparse.OptionParser()
parser.add_option('-p', '--port', dest='port', default=7000, type=int, help="set listener port")
(opts, args) = parser.parse_args()

log = logging.getLogger("pesterproxy")
log.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('pesterproxy.log')
fh.setLevel(logging.INFO)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s [%(levelname)s] --> %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
log.addHandler(fh)
log.addHandler(ch)

listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.bind(('', opts.port))
listener.listen(10)
threads = []
stopped = False

def handle_client(client, address):
  server = None
  try:
    log.info("Client accepted: %s", address[0])
    log.debug("Connecting to server...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect(("irc.mindfang.org", 6667))
    log.debug("Connected to server")
    broken = False
    while True:
      if broken: log.info("Client left: %s", address[0]); break
      log.debug("Waiting for activity")
      inputready,outputready,exceptready = select.select([server, client], [], [])
      log.debug("Handling activity")
      for s in inputready:
        log.debug("Reading from socket")
        if s == client:
          txt = client.recv(1024).decode('utf-8') # receive up to 1K bytes this should be more than enough for IRC
          log.debug("Outgoing: %s", txt)
          target = server
        elif s == server:
          txt = server.recv(1024).decode('utf-8') # receive up to 1K bytes
          log.debug("Incoming: %s", txt.encode('ascii', 'replace'))
          target = client
          txt = re.sub(r"(?i)</?[ibu]>", "", re.sub(r"(?i)</?c(=.*?)?>", "", txt))
          if "PESTERCHUM:" in txt:
            continue
        if not txt or stopped:
          client.close()
          server.close()
          broken = True
        else:
          log.debug("Transferring")
          target.send(bytes(txt+"\n", 'UTF-8'))
          log.debug("Transferred")
  except Exception as e:
    log.error("Error with Client %s", address[0])
    log.error("Reason: %s", e)
    log.error("Traceback: %s", traceback.format_exc())
  finally:
    client.close()
    server.close()

try:
  while True:
    log.debug("Accepting clients")
    client, address = listener.accept()
    if client:
      #handle_client(client)
      t = threading.Thread(target=handle_client, args=(client,address))
      threads.append(t)
      t.start()

except KeyboardInterrupt:
  log.info("Breaking out")
  log.info("Reason: KeyboardInterrupt")
except Exception as e:
  log.error("Breaking out")
  log.error("Reason: %s", e)
  log.error("Traceback: %s", traceback.format_exc())
finally:
  log.debug("Closing connections")
  stopped = True
  for t in threads:
    t.join()
  listener.shutdown(socket.SHUT_RDWR)
  listener.close()
print("Goodbye")
