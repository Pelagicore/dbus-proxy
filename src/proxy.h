/*
 * Copyright (C) 2013, Pelagicore AB   <jonatan.palsson@pelagicore.com>
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
 */

#include <dbus/dbus.h>
#include <dbus/dbus-glib.h>

/*! \brief Listen for new connections
 *
 * Listen for new connections, and once a new connection is received send this
 * over to the new_connection_cb () callback function
 */
void start_bus();

gboolean is_allowed (const char *direction, const char *interface,
                     const char *path, const char *member);
gboolean is_conn_known_eavesdropper (const char *unique_name);
gboolean remove_name_from_known_eavesdroppers (const char *unique_name);
gboolean is_incoming_eavesdropping (DBusMessage *msg);

// External
pid_t fork();
pid_t getpid();
