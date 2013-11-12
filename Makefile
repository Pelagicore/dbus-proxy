PREFIX ?= /usr

all: dbus-proxy

dbus-proxy: proxy.c
	$(CC) -o $@ $< `pkg-config --cflags --libs dbus-1 dbus-glib-1 jansson`

clean:
	rm -f dbus-proxy

install: dbus-proxy
	install -D -m 755 dbus-proxy $(DESTDIR)$(PREFIX)/bin/dbus-proxy
