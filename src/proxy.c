/*
 * Copyright (C) 2013-2016, Pelagicore AB   <joakim.gross@pelagicore.com>
 * Copyright (C) 2011, Stéphane Graber <stgraber@stgraber.org>
 * Copyright (C) 2010, Alban Crequy    <alban.crequy@collabora.co.uk>
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 * Boston, MA  02110-1301, USA.
 *
 * For further information see LICENSE
 */


#include "proxy.h"
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <stdlib.h>
#include <dbus/dbus-glib-lowlevel.h>
#include <jansson.h>

/*! the connection to dbus_srv from a local client, or NULL */
DBusConnection  *dbus_conn    = NULL;

/*! the connection to the real server */
DBusGConnection *master_conn  = NULL;

DBusServer *dbus_srv = NULL;

/*! JSON filter rules read from file */
json_t          *json_filters = NULL;

/*! D-Bus address to listen on */
gchar           *address      = NULL;

/*! Enable this for debus output */
gboolean         verbose      = FALSE;

/*! Bus type to create */
DBusBusType      bus          = DBUS_BUS_SESSION;

/*! List of connections that are to be ignored */
GList           *eavesdropping_conns = NULL;

void handle_sigchld(int sig) {
  while (waitpid((pid_t)(-1), 0, WNOHANG) > 0) {}
}


/*! \brief Filter for outgoing D-Bus requests
 *
 * This is called upon every sent D-Bus message. The message is compared to a
 * set of rules, and depending on these rules the message is either forwarded
 * or dropped
 *
 * \param conn      The D-Bus connection to filter
 * \param msg       The message to filter
 * \param user_data Unused (required by D-Bus API)
 * \return DBUS_HANDLER_RESULT_HANDLED         if the request is accepted
 * \return DBUS_HANDLER_RESULT_NOT_YET_HANDLED if the request is denied
 */
DBusHandlerResult filter_cb (DBusConnection *conn,
                             DBusMessage    *msg,
                             void           *user_data)
{
	/* Data arriving from client */
	guint32           serial;
	DBusHandlerResult retval = DBUS_HANDLER_RESULT_HANDLED;

	/* Handle Hello */
	if (dbus_message_get_type (msg) ==
	                DBUS_MESSAGE_TYPE_METHOD_CALL         &&
	                strcmp (dbus_message_get_path(msg),
	                        "/org/freedesktop/DBus") == 0 &&
	                strcmp (dbus_message_get_interface(msg),
	                        "org.freedesktop.DBus")  == 0 &&
	                strcmp (dbus_message_get_destination(msg),
	                        "org.freedesktop.DBus")  == 0 &&
	                strcmp (dbus_message_get_member (msg), "Hello") == 0) {

		      DBusMessage *welcome;
		const gchar       *dbus_local_name;

		dbus_local_name = dbus_bus_get_unique_name (
		         dbus_g_connection_get_connection(master_conn));

		if (verbose) {
			g_print("Hello received\n");
		}

		welcome = dbus_message_new_method_return (msg);
		if (!dbus_message_append_args (welcome,
			                       DBUS_TYPE_STRING,
			                       &dbus_local_name,
			                       DBUS_TYPE_INVALID)) {
			g_printerr("Cannot reply to Hello message\n");
			exit(1);
		}
		dbus_connection_send(conn, welcome, &serial);

		dbus_message_unref (welcome);
		goto out;
	}

	/* Handle Disconnected */
	if (dbus_message_get_type(msg) ==
		        DBUS_MESSAGE_TYPE_SIGNAL                   &&
		        strcmp (dbus_message_get_interface (msg),
		                "org.freedesktop.DBus.Local") == 0 &&
		        strcmp (dbus_message_get_member (msg),
		                "Disconnected")               == 0) {

		/* connection was disconnected */
		if (verbose) {
			g_print("connection was disconnected\n");
		}

		dbus_connection_close (dbus_conn);
		dbus_connection_unref (dbus_conn);
		dbus_conn = NULL;
		exit(0);
		goto out;
	}

	/* Forward */
	if (dbus_message_get_interface (msg) == NULL ||
	                 strcmp (dbus_message_get_interface(msg),
		                 "org.freedesktop.DBus") == 0)
	{
		dbus_connection_send(
		                dbus_g_connection_get_connection(master_conn),
		                msg,
		                &serial);
	} else if (is_allowed("outgoing",
		              dbus_message_get_interface (msg),
		              dbus_message_get_path      (msg),
		              dbus_message_get_member    (msg)))
	{
		g_print ("Accepted call to '%s' from "
		                "client to '%s' on '%s'.\n",
		        dbus_message_get_member   (msg),
		        dbus_message_get_interface(msg),
		        dbus_message_get_path     (msg));

		dbus_connection_send (
		                dbus_g_connection_get_connection (master_conn),
		                msg,
		                &serial);
	} else {
		g_print ("Rejected call to '%s' from "
		                "client to '%s' on '%s'.\n",
		        dbus_message_get_member    (msg),
		        dbus_message_get_interface (msg),
		        dbus_message_get_path      (msg));
		retval = DBUS_HANDLER_RESULT_NOT_YET_HANDLED;
	}

out:
	return retval;
}

/*! \brief compares if the comparison is contained by string
 *
 * \param  comparison The field to compare
 * \param  string The field in the rule
 * \return TRUE       if the rule matches the comparison
 * \return FALSE      if there is no match
 */
inline gboolean compare_entry(const char *comparison, const gchar  *string) {
	if (verbose) {
	    g_print("will try matching %s with %s\n", string, comparison);
    }

    if ((strcmp (string, "") != 0) && g_pattern_match_simple (string, comparison)) {
        if (verbose) {
            g_print("was a match\n");
        }
        return TRUE;
    } else {
        if (verbose) {
            g_print("no match\n");
        }
        return FALSE;
    }
}

/*! \brief Match a JSON rule against an entry
 *
 * Compare a rule as defined in the JSON rules file against the incoming or
 * outgoing message. This is a helper function for is_allowed().
 *
 * \param  rule       The JSON rule
 * \param  entry      The JSON field to compare against
 * \param  comparison The field to compare in the rule
 * \return TRUE       if the rule matches the comparison
 * \return FALSE      if there is no match
 */
gboolean match_rule(const json_t *rule,
                    const char   *entry,
                    const char   *comparison)
{
	json_t *json_entry;
	gchar  *string;

	json_entry = json_object_get(rule, entry);


	if (!json_is_string (json_entry)) {
		return FALSE;
	}

	string = (gchar*) json_string_value (json_entry);
	return compare_entry(comparison, string);
}

/*! \brief Match a JSON method against an entry
 *
 * Compare a method as defined in the JSON rules file against the incoming or
 * outgoing message. This is a helper function for is_allowed().
 *
 * \param  rule       The JSON rule
 * \param  comparison The field to compare in the rule
 * \return TRUE       if the rule matches the comparison
 * \return FALSE      if there is no match
 */
gboolean match_method(const json_t *rule, const char *comparison)
{
    json_t *json_entry;
    gchar  *string;

    json_entry = json_object_get(rule, "method");
    if (json_is_array(json_entry)) {
        size_t ix;
        json_t *val;

        json_array_foreach(json_entry, ix, val) {
            if (!json_is_string(val)) {
                if (verbose) {
                    g_print("Entry in method array is not a string.");
                }
                return FALSE;
            }

            string = (gchar*) json_string_value (val);
            if ((strcmp (string, "") != 0) && g_pattern_match_simple (string, comparison)) {
                if (verbose) {
                    g_print("was a match\n");
                }
                return TRUE;
            }
        }
    } else if (json_is_string (json_entry)) {
        string = (gchar*) json_string_value (json_entry);
        return compare_entry(comparison, string);
    }

    return FALSE;
}


/*! \brief Decide if a message is allowed
 *
 * Go through all the neccessary parameters of a message to decide whether it
 * is allowed or not
 *
 * \param direction Direction of the message
 * \param interface The interface the message was sent on
 * \param path      The object path of the message
 * \param member    The method of the message
 * \return TRUE     if the message is allowed
 * \return FALSE    if the message is now allowed
 */
gboolean is_allowed (const char *direction,
                     const char *interface,
                     const char *path,
                     const char *member)
{
	size_t    i;
	json_t   *rule;
	gboolean  direction_ok, interface_ok, object_path_ok, method_ok;

	/* Check all rules until a match is found. When a match is found we
	   don't check any following rules. This means that a more permissive
	   rule will trump less permissive rules. */
	for (i = 0; i < json_array_size (json_filters); i++) {
		direction_ok, interface_ok, object_path_ok, method_ok = FALSE;

		/* Get the JSON array containing the JSON objects */
		rule = json_array_get (json_filters, i);
		if (rule == NULL || !json_is_object (rule)) {
			json_decref (rule);
			break;
		}

		direction_ok   = match_rule (rule, "direction",   direction);
		interface_ok   = match_rule (rule, "interface",   interface);
		object_path_ok = match_rule (rule, "object-path", path);
		method_ok      = match_method(rule, member);

		/* All entries matched for the rule */
		if (direction_ok   &&
		    interface_ok   &&
		    object_path_ok &&
		    method_ok)
		{
			return TRUE;
		}

		/*
		 * Since direction seems to be a common source of errors, the
		 * following printout is added as a helper to developer
		 */
		if (!direction_ok   &&
		     interface_ok   &&
		     object_path_ok &&
		     method_ok)
		{
			g_print("Direction '%s' does not match but "
			        "everything else does\n", direction);
		}
	}

	return FALSE;
}

/*! \brief Filter for incoming D-Bus requests
 *
 * This is called upon every received D-Bus message. The message is compared to
 * a set of rules, and depending on these rules the message is either forwarded
 * or dropped
 *
 * \param conn      The D-Bus connection to filter
 * \param msg       The message to filter
 * \param user_data Unused (required by D-Bus API)
 * \return DBUS_HANDLER_RESULT_HANDLED         if the request is accepted
 * \return DBUS_HANDLER_RESULT_NOT_YET_HANDLED if the request is denied
 */
DBusHandlerResult master_filter_cb (DBusConnection *conn,
                                    DBusMessage    *msg,
                                    void           *user_data)
{
	/* Data arriving from server */

	guint32           serial;
	DBusHandlerResult retval = DBUS_HANDLER_RESULT_HANDLED;

	if (!dbus_conn) {
		exit(1);
	}
	/* Make sure that a new connection does not have a unique name
	   that was previously owned by an eavesdropping connection */
	if (dbus_message_get_member(msg) != NULL &&
	    strcmp(dbus_message_get_member(msg), "NameAcquired") == 0)
	{
		const char *dest = dbus_message_get_destination(msg);
		if (verbose)
		{
			g_print ("NameAcquired received by %s\n", dest);
		}

		if (dest != NULL &&
		    is_conn_known_eavesdropper(dest))
		{
			if (verbose)
			{
				g_print("New connection's unique name ('%s')"
					" was previously known as an eavesdropper."
					" Removed old entry...\n", dest);
			}
			remove_name_from_known_eavesdroppers(dest);
		}
	}

	/* Forward */
	if (dbus_message_get_interface(msg) == NULL ||
	    strcmp(dbus_message_get_interface(msg),
	           "org.freedesktop.DBus")  == 0)
	{
		if (is_incoming_eavesdropping(msg) &&
		    !is_conn_known_eavesdropper(dbus_message_get_sender(msg)))
		{
			eavesdropping_conns =
			    g_list_append (eavesdropping_conns,
					   (gpointer) dbus_message_get_sender(msg));
		}

		dbus_connection_send(dbus_conn, msg, &serial);
	} else if (is_conn_known_eavesdropper (dbus_bus_get_unique_name(conn)))
	{
		if (verbose) {
			g_print ("'%s' is an eavesdropping connection, let it go...\n",
				 dbus_bus_get_unique_name(conn));
		}
	} else if (is_allowed("incoming",
	           dbus_message_get_interface (msg),
	           dbus_message_get_path      (msg),
	           dbus_message_get_member    (msg)))
	{
		g_print("Accepted call to '%s' from server to '%s' on '%s'.\n",
		        dbus_message_get_member    (msg),
		        dbus_message_get_interface (msg),
		        dbus_message_get_path      (msg));
		dbus_connection_send(dbus_conn, msg, &serial);
	} else {
		g_print("Rejected call to '%s' from server to '%s' on '%s'.\n",
		        dbus_message_get_member    (msg),
		        dbus_message_get_interface (msg),
		        dbus_message_get_path      (msg));
		retval = DBUS_HANDLER_RESULT_NOT_YET_HANDLED;
	}

	return retval;
}

/*! \brief Allow all connections to the D-Bus socket
 *
 * By returning true here regardless of input data, any user may communicate
 * using the proxied D-Bus socket.
 * \return TRUE
 */
dbus_bool_t allow_all_connections (DBusConnection *conn,
                                   unsigned long   uid,
                                   void           *data)
{
	return TRUE;
}

/*! \brief Test if a new connection has signaled that it wants to eavesdrop
 *
 * If a new connection is eavesdropping (for instance like the dbus-monitor)
 * the D-Bus proxy will keep track of it and make sure that it does not
 * hijack the messages.
 *
 * \param msg The D-Bus message sent to org.freedesktop.DBus
 * \return TRUE If connection wants to eavesdrop
 * \return FALSE If connection does not want to eavesdrop
 */
gboolean is_incoming_eavesdropping (DBusMessage *msg)
{
	gboolean is_eavesdropping = FALSE;

	/* Look for AddMatch and eavesdrop=true in message */
	if (dbus_message_get_member(msg) != NULL &&
	    strcmp(dbus_message_get_member(msg), "AddMatch") == 0)
        {
		const char *msg_arguments;
		dbus_message_get_args (msg,
				       NULL,
				       DBUS_TYPE_STRING,
				       &msg_arguments);

		if (strstr(msg_arguments, "eavesdrop=true") != NULL)
		{
			is_eavesdropping = TRUE;
			if (verbose)
			{
				g_print ("'%s' AddMatch-args: \"%s\"\n",
					 dbus_message_get_sender(msg),
					 msg_arguments);
			}
		}
        }
	return is_eavesdropping;
}

/*! \brief Test if existing connection is an eavesdropping connection
 *
 * Tests if the connection passed as argument is in the list of known
 * eavesdropping connections.
 *
 * \param unique_name The unique name of the D-Bus connection to test
 * \return TRUE Connection is an eavesdropping connection
 * \return FALSE Connection is not an eavesdropping connection
 */
gboolean is_conn_known_eavesdropper (const char *unique_name)
{
	gboolean found = FALSE;
	GList *iter = eavesdropping_conns;

	while (iter != NULL)
	{
		if (strcmp(unique_name, (char*) iter->data) == 0)
		{
			found = TRUE;
			break;
		}
		iter = iter->next;
	}

	return found;
}

/*! \brief Removes a unique name from the list of eavesdroppers
 *
 * Removes a unique name from the list of eavesdropping connections.
 * If an eavesdropping connection is disconnected, then the unique
 * name will still be stored in the list of eavesdropping connections
 * until explicitly removed (e.g. when a new connection is assigned
 * with the same unique name by the bus).
 *
 * \param unique_name The unique name of the D-Bus connection to be removed
 * \return TRUE If connection was found and removed
 * \return FALSE If connection could not be found
 */
gboolean remove_name_from_known_eavesdroppers (const char *unique_name)
{
	gboolean removed = FALSE;
	GList *iter = eavesdropping_conns;

	while (iter != NULL)
	{
		if (strcmp(unique_name, (char*) iter->data) == 0)
		{
			eavesdropping_conns =
			  g_list_remove (eavesdropping_conns, iter->data);
			removed = TRUE;
		}
		iter = iter->next;
	}

	return removed;
}

/*! \brief Accept a new connection
 *
 * This is called with each new connection. The process will fork off a new
 * thread in which filter rules are applied and the incoming messages are
 * filtered. The parent process goes back to listening for new connections
 *
 * \param server The D-Bus server
 * \param conn   The D-Bus connection to filter
 * \param data   Unused (needed by D-Bus API)
 */
void new_connection_cb (DBusServer *server, DBusConnection *conn, void *data) {
	pid_t   pid;
	pid_t   forked;
	GError *error = NULL;

	forked = fork();
	pid    = getpid();

	if (forked != 0) {
		if (verbose)
			g_print ("in main process, pid: %d\n", pid);

		/* Reconfigure the master socket as forking will break it */
		start_bus();
		return;
	} else {
		if (verbose)
			g_print ("in child process, pid: %d\n", pid);
	}

	if (master_conn != NULL) {
		g_print ("master_conn already initialized\n");
		exit (1);
	}

	if (dbus_conn != NULL) {
		g_print("dbus_conn already initialized\n");
		exit (1);
	}

	/* Init master connection */
	master_conn = dbus_g_bus_get (bus, &error);
	if (!master_conn) {
		g_printerr ("Failed to open connection to bus: %s\n",
		            error->message);
		g_clear_error (&error);
		exit(1);
	}

	dbus_connection_add_filter (
	        dbus_g_connection_get_connection(master_conn),
		master_filter_cb,
		NULL,
		NULL);

	if (verbose) {
		g_print("New connection\n");
	}

	dbus_connection_ref               (conn);
	dbus_connection_setup_with_g_main (conn, NULL);
	dbus_connection_add_filter        (conn, filter_cb, NULL, NULL);

	dbus_connection_set_unix_user_function (conn,
	                                        allow_all_connections,
	                                        NULL,
	                                        NULL);

	dbus_connection_set_allow_anonymous (conn, TRUE);
	dbus_conn = conn;
}

void start_bus() {
	DBusError   error;

	dbus_error_init (&error);

	if (dbus_srv != NULL) {
		dbus_server_disconnect(dbus_srv);
		dbus_server_unref(dbus_srv);
	}
	dbus_srv = dbus_server_listen (address, &error);
	if (dbus_srv == NULL) {
		g_printerr("Cannot listen on %s\n", address);
		exit(1);
	}

	dbus_server_set_new_connection_function (dbus_srv,
	                                         new_connection_cb,
	                                         NULL,
	                                         NULL);
	dbus_server_setup_with_g_main (dbus_srv, NULL);
}

/*! \brief Read filter rules from JSON
 *
 * Populate the json_filters global variable with the filter rules read from
 * the JSON configuration which comes in via stdin
 *
 * \param section The section in the JSON config to use
 * \return 0      Upon success
 * \return 1      Upon failure
 */
int parse_json_from_stdin (const char *section) {
	size_t        i;
	json_error_t  error;
	json_t       *root, *config, *rule;
	char         *full_section = calloc (sizeof (char), 30);
	int           retval = 0;
	int config_found = 0;

	snprintf (full_section, 30, "dbus-gateway-config-%s", section);

	/* Allow multiple configuration snippets, each as it's own root obj */
	do {

		/* Get root JSON object */
		root = json_loadf (stdin, JSON_DISABLE_EOF_CHECK, &error);

		if (!root) {
			/* If no config was found this is an error, otherwise it's normal */
			if (!config_found) {
				g_printerr ("error: on line %d: %s\n", error.line, error.text);
				retval = 1;
			}
			break;
		}

		/* We have atleast one root object in file */
		config_found = 1;

		// Get array
		config = json_object_get (root, full_section);

		if (!json_is_array(config)) {
			g_printerr("error: %s is not present in config, or not an array. "
					"Fix your config\n", full_section);
			json_decref (config);
			retval = 1;
			break;
		}
		if (NULL == json_filters) {
			json_filters = config;
		} else {
			if (0 != json_array_extend(json_filters, config)){
				g_printerr("Error extending config array\n");
			}
		}
	} while (root);

	return retval;
}

int main(int argc, char *argv[]) {
	GMainLoop *mainloop = NULL;
	GError    *error    = NULL;

	/* Extract address */
	if (argc < 3) {
		g_print("Usage: dbus-proxy address session|system\n"
		        "waits for JSON conf at stdin.\n");
		exit(1);
	}

	address = g_strconcat("unix:path=", argv[1], NULL);
	if (strcmp (argv[2], "system") == 0) {
		bus = DBUS_BUS_SYSTEM;
	} else if (strcmp(argv[2], "session") == 0) {
		bus = DBUS_BUS_SESSION;
	} else {
		g_print ("Must give bus type as second argument (either session or system).\n");
		exit (1);
	}

	/* Parse JSON */
	if (parse_json_from_stdin (argv[2]) == 1){
		g_print ("Something wrong with JSON file. Exiting...\n");
		exit (1);
	}

	struct sigaction sa;
	sa.sa_handler = &handle_sigchld;
	sigemptyset(&sa.sa_mask);
	sa.sa_flags = SA_RESTART | SA_NOCLDSTOP;
	if (sigaction(SIGCHLD, &sa, 0) == -1) {
		perror(0);
		exit(1);
	}

	/* Start listening */
	start_bus ();
	mainloop = g_main_loop_new (NULL, FALSE);
	g_main_loop_run (mainloop);

	return 0;
}
