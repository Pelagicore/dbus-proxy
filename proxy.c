#include "proxy.h"
#include <stdlib.h>
#include <dbus/dbus.h>
#include <dbus/dbus-glib.h>
#include <dbus/dbus-glib-lowlevel.h>

/* the connection to dbus_srv from a local client, or NULL */
DBusConnection *dbus_conn = NULL;

/* the connection to the real server */
DBusGConnection *master_conn = NULL;

gboolean verbose = FALSE;
gchar *address = NULL;
gchar **filters = NULL;

DBusHandlerResult filter_cb(DBusConnection *conn, DBusMessage *msg, void *user_data) {
    // Data arriving from client

    guint32 serial;
    DBusHandlerResult retval = DBUS_HANDLER_RESULT_HANDLED;

    // Handle Hello
    if (dbus_message_get_type(msg) == DBUS_MESSAGE_TYPE_METHOD_CALL && strcmp(dbus_message_get_path(msg),
        "/org/freedesktop/DBus") == 0 &&
      strcmp(dbus_message_get_interface(msg),
        "org.freedesktop.DBus") == 0 &&
      strcmp(dbus_message_get_destination(msg),
        "org.freedesktop.DBus") == 0 &&
      strcmp(dbus_message_get_member(msg), "Hello") == 0) {

        DBusMessage *welcome;
        /* our unique D-Bus name on the real bus */
        const gchar *dbus_local_name;

        dbus_local_name = dbus_bus_get_unique_name(dbus_g_connection_get_connection(master_conn));

        if (verbose) {
            g_print("Hello received\n");
        }

        welcome = dbus_message_new_method_return(msg);
        if (!dbus_message_append_args(welcome, DBUS_TYPE_STRING, &dbus_local_name, DBUS_TYPE_INVALID)) {
            g_printerr("Cannot reply to Hello message\n");
            exit(1);
        }
        dbus_connection_send(conn, welcome, &serial);

        goto out;
    }

    // Handle Disconnected
    if (dbus_message_get_type(msg) == DBUS_MESSAGE_TYPE_SIGNAL &&
      strcmp(dbus_message_get_interface(msg),
        "org.freedesktop.DBus.Local") == 0 &&
      strcmp(dbus_message_get_member(msg), "Disconnected") == 0) {

        /* connection was disconnected */
        if (verbose) {
            g_print("connection was disconnected\n");
        }
        dbus_connection_close(dbus_conn);
        dbus_connection_unref(dbus_conn);
        dbus_conn = NULL;
        exit(0);
        goto out;
    }

    // Forward
    if (dbus_message_get_interface(msg) == NULL || strcmp(dbus_message_get_interface(msg), "org.freedesktop.DBus") == 0) {
        dbus_connection_send(dbus_g_connection_get_connection(master_conn), msg, &serial);
    }
    else if (is_allowed("outgoing", dbus_message_get_interface(msg), dbus_message_get_path(msg), dbus_message_get_member(msg))) {
        g_print("Accepted call to '%s' from client to '%s' on '%s'.\n", dbus_message_get_member(msg), dbus_message_get_interface(msg), dbus_message_get_path(msg));
        dbus_connection_send(dbus_g_connection_get_connection(master_conn), msg, &serial);
    }
    else {
        g_print("Rejected call to '%s' from client to '%s' on '%s'.\n", dbus_message_get_member(msg), dbus_message_get_interface(msg), dbus_message_get_path(msg));
        retval = DBUS_HANDLER_RESULT_NOT_YET_HANDLED;
    }

out:
    return retval;
}

gboolean is_allowed(const char *direction, const char *interface, const char *path, const char *member) {
    gchar *rule = "";
    gint index = 0;
    gchar *query = "";

    query = g_strconcat(direction, ";", interface, ";", path, ";", member, NULL);

    while (1) {
        rule=filters[index];
        if (rule == NULL) {
            break;
        }

        if (strcmp(rule, "") != 0) {
            if (g_pattern_match_simple(rule, query)) {
                return TRUE;
            }
        }

        index = index + 1;
    }

    return FALSE;
}

DBusHandlerResult master_filter_cb(DBusConnection *conn, DBusMessage *msg, void *user_data) {
    // Data arriving from server

    guint32 serial;
    DBusHandlerResult retval = DBUS_HANDLER_RESULT_HANDLED;

    if (!dbus_conn) {
        exit(1);
    }

    // Forward
    if (dbus_message_get_interface(msg) == NULL || strcmp(dbus_message_get_interface(msg), "org.freedesktop.DBus") == 0) {
        dbus_connection_send(dbus_conn, msg, &serial);
    }
    else if (is_allowed("incoming", dbus_message_get_interface(msg), dbus_message_get_path(msg), dbus_message_get_member(msg))) {
        g_print("Accepted call to '%s' from server to '%s' on '%s'.\n", dbus_message_get_member(msg), dbus_message_get_interface(msg), dbus_message_get_path(msg));
        dbus_connection_send(dbus_conn, msg, &serial);
    }
    else {
        g_print("Rejected call to '%s' from server to '%s' on '%s'.\n", dbus_message_get_member(msg), dbus_message_get_interface(msg), dbus_message_get_path(msg));
        retval = DBUS_HANDLER_RESULT_NOT_YET_HANDLED;
    }

    return retval;
}

dbus_bool_t allow_all_connections(DBusConnection *conn, unsigned long uid, void *data) {
    return TRUE;
}

void new_connection_cb(DBusServer *server, DBusConnection *conn, void *data) {
    pid_t pid;
    pid_t forked;
    GError *error = NULL;

    forked = fork();
    pid = getpid();

    if (forked != 0) {
        if (verbose) {
            g_print("in main process, pid: %d\n", pid);
        }

        // Reconfigure the master socket as forking will break it
        start_bus();
        return;
    }
    else {
        if (verbose) {
            g_print("in child process, pid: %d\n", pid);
        }
    }

    if (master_conn != NULL) {
        g_print("master_conn already initialized\n");
        exit(1);
    }

    if (dbus_conn != NULL) {
        g_print("dbus_conn already initialized\n");
        exit(1);
    }

    // Init master connection
    master_conn = dbus_g_bus_get(DBUS_BUS_SESSION, &error);
    if (!master_conn) {
        g_printerr("Failed to open connection to session bus: %s\n", error->message);
        g_clear_error(&error);
        exit(1);
    }

    dbus_connection_add_filter(dbus_g_connection_get_connection(master_conn), master_filter_cb, NULL, NULL);

    if (verbose) {
        g_print("New connection\n");
    }

    dbus_connection_ref(conn);
    dbus_connection_setup_with_g_main(conn, NULL);
    dbus_connection_add_filter(conn, filter_cb, NULL, NULL);
    dbus_connection_set_unix_user_function(conn, allow_all_connections, NULL, NULL);
    dbus_connection_set_allow_anonymous(conn, TRUE);
    dbus_conn = conn;
}

void start_bus() {
    DBusServer *dbus_srv;
    DBusError error;

    dbus_error_init(&error);

    dbus_srv = dbus_server_listen(address, &error);
    if (dbus_srv == NULL) {
        g_printerr("Cannot listen on\n");
        exit(1);
    }

    dbus_server_set_new_connection_function(dbus_srv, new_connection_cb, NULL, NULL);
    dbus_server_setup_with_g_main(dbus_srv, NULL);
}

int main(int argc, char *argv[]) {
    GMainLoop *mainloop = NULL;
    GError *error = NULL;
    gchar * content = "*;*;*;*";

    // Extract address
    if (argc < 2) {
        g_print("Must give socket path and optionaly config as parameter.\n");
        exit(1);
    }

    address = g_strconcat("unix:path=", argv[1], NULL);

    if (argc > 2) {
        g_file_get_contents(argv[2], &content, NULL, NULL);
    }
    filters = g_strsplit(content,"\n",0);


    // Start listening
    g_type_init();
    start_bus();
    mainloop = g_main_loop_new(NULL, FALSE);
    g_main_loop_run(mainloop);

    return 0;
}
