#include "proxy.h"
#include <stdlib.h>
#include <dbus/dbus.h>
#include <dbus/dbus-glib.h>
#include <dbus/dbus-glib-lowlevel.h>
#include <jansson.h>

/* the connection to dbus_srv from a local client, or NULL */
DBusConnection *dbus_conn = NULL;

/* the connection to the real server */
DBusGConnection *master_conn = NULL;

gboolean verbose = FALSE;
gchar *address = NULL;
DBusBusType bus = DBUS_BUS_SESSION;
json_t *json_filters = NULL;

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

gboolean match_rule(const json_t* rule, const char *entry, const char *comparison) {
    json_t *json_entry;
    gchar *string;

    json_entry = json_object_get(rule, entry);
    if (!json_is_string(json_entry)) {
        return FALSE;
    }
    string = (gchar*) json_string_value(json_entry);
    if (strcmp(string, "") != 0 && g_pattern_match_simple(string, comparison)) {
	return TRUE;
    }
    else {
	return FALSE;
    }
}

gboolean is_allowed(const char *direction, const char *interface, const char *path, const char *member) {
    size_t i;
    json_t *rule;
    gboolean direction_ok, interface_ok, object_path_ok, method_ok;

    for (i = 0; i < json_array_size(json_filters); i++) {
	direction_ok, interface_ok, object_path_ok, method_ok = FALSE;

	// Get the JSON array containing the JSON objects
	rule = json_array_get(json_filters, i);
        if (rule == NULL || !json_is_object(rule)) {
	    json_decref(rule);
	    break;
        }

	direction_ok = match_rule(rule, "direction", direction);
        interface_ok = match_rule(rule, "interface", interface);
        object_path_ok = match_rule(rule, "object-path", path);
        method_ok = match_rule(rule, "method", member);

	// All entries matched for the rule
	if (direction_ok && interface_ok && object_path_ok && method_ok) {
	    return TRUE;
	}

	// Since direction seems to be a common source of errors, the following
	// printout is added as a helper to developer
	if (!direction_ok && interface_ok && object_path_ok && method_ok) {
	    g_print("Direction '%s' does not match but everything else does\n", direction);
	}
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
    master_conn = dbus_g_bus_get(bus, &error);
    if (!master_conn) {
        g_printerr("Failed to open connection to bus: %s\n", error->message);
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

int parse_json_file(const char *path) {
    size_t i;
    json_error_t error;
    json_t *root, *config, *rule;

    // Get root JSON object
    root = json_load_file(path, 0, &error);

    if(!root) {
        g_printerr("error: on line %d: %s\n", error.line, error.text);
        return 1;
    }

    // Get array
    config = json_object_get(root, "dbus-proxy-config");
    
    if(!json_is_array(config)) {
        g_printerr("error: config is not an array\n");
	json_decref(config);
	return 1;
    }
    json_filters = config;

    return 0;
}

int main(int argc, char *argv[]) {
    GMainLoop *mainloop = NULL;
    GError *error = NULL;

    // Extract address
    if (argc < 3) {
        g_print("Must give socket path, bus type, and optionaly config as parameter.\n");
        exit(1);
    }

    address = g_strconcat("unix:path=", argv[1], NULL);
    if (strcmp(argv[2], "system") == 0) {
        bus = DBUS_BUS_SYSTEM;
    }
    else if (strcmp(argv[2], "session") == 0) {
        bus = DBUS_BUS_SESSION;
    }
    else {
        g_print("Must give bus type as second argument (either session or system).\n");
        exit(1);
    }

    if (argc > 3) {
        if (!g_file_test(argv[3], G_FILE_TEST_EXISTS)) {
		g_print ("Configuration file '%s' does not exist\n", argv[3]);
		exit (1);
	}

	// Parse JSON
	if (parse_json_file(argv[3]) == 1){
	    g_print("Something wrong with JSON file. Exiting...\n");
	    exit(1);
	}
    }

    // Start listening
    g_type_init();
    start_bus();
    mainloop = g_main_loop_new(NULL, FALSE);
    g_main_loop_run(mainloop);

    return 0;
}
