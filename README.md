pesterproxy
===========

PesterProxy is a really simple IRC proxy which strips most of the underlying Pesterchum formatting from IRC messages, making the use of alternate IRC clients slightly easier.

Example:
```
<c=0,0,0>EB: <c=255,0,0>Hello</c> <b>world!</b></c>
```

becomes


```
EB: Hello world!
```

By default, PesterProxy listens on port 7000 for new connections, this can be changed using the cli arguments.

```
Usage: pesterchum-proxy.py [options]

Options:
  -h, --help            show this help message and exit
  -p PORT, --port=PORT  set listener port
```
