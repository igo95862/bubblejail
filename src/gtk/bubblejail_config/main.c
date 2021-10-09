/* SPDX-License-Identifier: GPL-3.0-or-later */
/*
  Copyright 2019-2021 igo95862, ls0h

  This file is part of bubblejail.
  bubblejail is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.
  bubblejail is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  You should have received a copy of the GNU General Public License
  GNU General Public License for more details.
  along with bubblejail.  If not, see <https://www.gnu.org/licenses/>.
*/

#include "bubblejail_config.h"

const gint gnome_recommended_horizontal_spacing = 12;

static void
activate(GtkApplication *app,
         gpointer G_GNUC_UNUSED user_data)
{

    GtkWindow *main_window = GTK_WINDOW(gtk_application_window_new(app));
    gtk_window_set_default_size(main_window, 640, 500);

    show_instance_list(main_window);
}

int main(int argc,
         char **argv)
{
    GtkApplication *app = gtk_application_new("org.bubblejail.Config", G_APPLICATION_FLAGS_NONE);

    g_signal_connect(app, "activate", G_CALLBACK(activate), NULL);

    int status = g_application_run(G_APPLICATION(app), argc, argv);
    g_object_unref(app);

    return status;
}
