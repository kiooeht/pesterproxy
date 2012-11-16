#!/usr/bin/env python3
import logging
from logging.handlers import RotatingFileHandler
import traceback
import socket
import select
import re
import threading
import struct
import optparse
import sys

parser = optparse.OptionParser()
parser.add_option('-p', '--port', dest='port', default=7000, type=int, help='set listener port')
parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='print more debug information')
(opts, args) = parser.parse_args()

log = logging.getLogger("pesterproxy")
if opts.verbose:
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)
# create file handler which logs even debug messages
fh = RotatingFileHandler('pesterproxy.log', maxBytes=1024*20, backupCount=4)
# create console handler with a higher log level
ch = logging.StreamHandler()
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

codes = [
    [255,255,255],
    [0,0,0],
    [0,0,127],
    [0,147,0],
    [255,0,0],
    [127,0,0],
    [156,0,156],
    [252,127,0],
    [255,255,0],
    [0,252,0],
    [0,147,147],
    [0,255,255],
    [0,0,252],
    [255,0,255],
    [127,127,127],
    [210,210,210]
]

colours = {
  "black":  (0,0,0),
  "white":  (255,255,255),
  "red":    (255,0,0),
  "green":  (0,255,0),
  "blue":   (0,0,255),
  "yellow": (255,255,0),
  "purple": (128,0,128),
  "violet": (238,130,238),
  "orange": (255,165,0),
  "cyan":   (0,255,255)
}

formats = {
  "b": "\u0002",
  "u": "\u001F",
  "i": "\u0016"
}

def fudge_it(rgb):
    diff = 256*3
    diff_i = None
    for i,code in enumerate(codes):
        d = sum([abs(code[x] - rgb[x]) for x in range(3)])
        if d <= diff:
            diff = d
            diff_i = i
    return codes[diff_i]

colour_stack = []
format_stack = []

def hex_to_rgb(hex):
    return struct.unpack('BBB', hex.decode('hex'))

def colour_to_irc(match):
  rgb = match.group(1).lower()
  rgb = rgb[rgb.find('=')+1:]
  if not rgb or rgb == 'c':
    if colour_stack:
      colour_stack.pop()
    code = "\u000F"
    for f in format_stack:
      code += f
    if len(colour_stack) > 0:
      code += colour_stack[-1]
    return code
  if rgb[0] == '#':
    rgb = hex_to_rgb(rgb[1:])
  elif rgb in colours:
    rgb = colours[rgb]
  else:
    try:
      rgb = [int(x) for x in rgb.split(",")]
    except:
      colour_stack.append("")
      return ""
  code = "\u0003" + str(codes.index(fudge_it(rgb)))
  colour_stack.append(code)
  return code

def format_to_irc(match):
  type = match.group(1).lower()
  if type[0] == '/':
    if format_stack:
      return format_stack.pop()
    else:
      return ""
  format_stack.append(formats[type])
  return formats[type]

def convert_to_irc(match):
  type = match.group(1).lower()
  if type[0] == 'c':
    return colour_to_irc(match)
  else:
   return format_to_irc(match)

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
          txt = re.sub(r"(?i)</?([bui]|c=?.*?)>", convert_to_irc, txt)
          colour_stack[:] = []
          format_stack[:] = []
          txt = [x for x in txt.split("\r\n") if "PESTERCHUM:" not in x]
          txt = "\r\n".join(txt)
          if txt == '':
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

