PREFIX ?= /usr

all: arkose-dbus-proxy

arkose-dbus-proxy: proxy.c
	$(CC) -o $@ $< `pkg-config --cflags --libs dbus-1 dbus-glib-1`

clean:
	rm -f arkose-dbus-proxy

install: arkose-dbus-proxy
	install -D -m 755 arkose-dbus-proxy $(DESTDIR)$(PREFIX)/bin/arkose-dbus-proxy
