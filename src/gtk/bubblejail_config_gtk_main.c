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

#include <gtk/gtk.h>

const gint gnome_recommended_horizontal_spacing = 12;
static GDBusConnection *dbus_connection = NULL;

static GDBusArgInfo bubblejail_manager_method_list_instaces = {
    .name = "list_of_instaces",
    .signature = "a(ss)",
    .ref_count = -1,
};

static GDBusMethodInfo bubblejail_manager_methods = {
    .name = "ListInstancesWithDesktopEntries",
    .ref_count = -1,
    .out_args = (GDBusArgInfo *[]){
        &bubblejail_manager_method_list_instaces,
        NULL,
    },
    .annotations = NULL,
};

static GDBusInterfaceInfo bubblejail_manager_info = {
    .name = "org.bubblejail.Manager.Unstable",
    .ref_count = -1,
    .methods = (GDBusMethodInfo *[]){
        &bubblejail_manager_methods,
        NULL,
    },
    .signals = NULL,
};

static GDBusProxy *bubblejail_manager_proxy = NULL;

GtkHeaderBar *create_instace_selection_header()
{
  GtkHeaderBar *instance_selection_header = GTK_HEADER_BAR(gtk_header_bar_new());
  gtk_header_bar_set_title(instance_selection_header, "Bubblejail Config");
  gtk_header_bar_set_subtitle(instance_selection_header, "Existing instances");

  gtk_header_bar_set_show_close_button(instance_selection_header, TRUE);

  GtkButton *create_instance_button = GTK_BUTTON(gtk_button_new());

  GtkBox *create_instance_box = GTK_BOX(gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6));
  gtk_box_pack_start(create_instance_box, gtk_image_new_from_icon_name("list-add-symbolic", GTK_ICON_SIZE_BUTTON), FALSE, FALSE, 0);
  gtk_box_pack_start(create_instance_box, gtk_label_new("New"), FALSE, FALSE, 0);

  gtk_container_add(GTK_CONTAINER(create_instance_button), GTK_WIDGET(create_instance_box));

  gtk_header_bar_pack_start(instance_selection_header, GTK_WIDGET(create_instance_button));

  return instance_selection_header;
}

typedef struct bubblejail_config_gtk_main_instance_list
{
  GtkScrolledWindow *scrolled_window;
  GtkListBox *list_box;
} BubblejailInstanceList;

static BubblejailInstanceList instances_list = {0};

BubblejailInstanceList create_instance_list()
{
  GtkScrolledWindow *new_instance_scrolled_window = GTK_SCROLLED_WINDOW(gtk_scrolled_window_new(NULL, NULL));

  GtkListBox *instances_list = GTK_LIST_BOX(gtk_list_box_new());
  gtk_list_box_set_selection_mode(instances_list, GTK_SELECTION_NONE);

  gtk_container_add(GTK_CONTAINER(new_instance_scrolled_window), GTK_WIDGET(instances_list));

  return (BubblejailInstanceList){
      .scrolled_window = new_instance_scrolled_window,
      .list_box = instances_list,
  };
}

typedef struct bubblejail_config_gtk_main_instance_list_item
{
  GtkButton *edit_button;
  GtkLabel *label;
  GtkBox *container;
} BubblejailInstanceListItem;

BubblejailInstanceListItem create_instance_list_entry(const gchar *label_text, const gchar *icon_name)
{
  if (icon_name == NULL)
  {
    icon_name = "system-run-symbolic";
  }

  GtkBox *container_box = GTK_BOX(gtk_box_new(GTK_ORIENTATION_HORIZONTAL, gnome_recommended_horizontal_spacing));
  gtk_box_set_homogeneous(container_box, FALSE);

  GtkImage *instance_icon = GTK_IMAGE(gtk_image_new_from_icon_name(icon_name, GTK_ICON_SIZE_LARGE_TOOLBAR));
  gtk_box_pack_start(container_box, GTK_WIDGET(instance_icon), FALSE, TRUE, 0);

  GtkLabel *instance_name_label = GTK_LABEL(gtk_label_new(label_text));
  gtk_box_pack_start(container_box, GTK_WIDGET(instance_name_label), FALSE, TRUE, 0);

  GtkButton *edit_button = GTK_BUTTON(gtk_button_new());
  GtkImage *edit_image = GTK_IMAGE(gtk_image_new_from_icon_name("applications-system-symbolic", GTK_ICON_SIZE_LARGE_TOOLBAR));
  gtk_button_set_image(edit_button, GTK_WIDGET(edit_image));
  gtk_box_pack_end(container_box, GTK_WIDGET(edit_button), FALSE, TRUE, 0);

  return (BubblejailInstanceListItem){
      .container = container_box,
      .edit_button = edit_button,
      .label = instance_name_label,
  };
}

void instance_list_insert(BubblejailInstanceList instance_list, BubblejailInstanceListItem new_item)
{
  gtk_container_add(GTK_CONTAINER(instance_list.list_box), GTK_WIDGET(new_item.container));
}

void update_instaces_list(GObject *source_object,
                          GAsyncResult *res,
                          gpointer G_GNUC_UNUSED(user_data))
{
  GError *error = NULL;

  GVariant *result_variant = g_dbus_proxy_call_finish(bubblejail_manager_proxy, res, &error);
  if (error != NULL)
  {
    g_abort();
  }
  g_assert_cmpstr(g_variant_get_type_string(result_variant), ==, "(a(ss))");

  GVariant *list_of_instances = g_variant_get_child_value(result_variant, 0);
  g_assert_cmpstr(g_variant_get_type_string(list_of_instances), ==, "a(ss)");

  GVariantIter iter = {0};
  GVariant *instance_struct = NULL;
  g_variant_iter_init(&iter, list_of_instances);
  while ((instance_struct = g_variant_iter_next_value(&iter)))
  {
    g_assert_cmpstr(g_variant_get_type_string(instance_struct), ==, "(ss)");
    const char *instance_name = NULL;
    const char *desktop_name = NULL;
    g_variant_get_child(instance_struct, 0, "s", &instance_name);
    g_variant_get_child(instance_struct, 1, "s", &desktop_name);

    g_assert(instance_name);

    BubblejailInstanceListItem new_instance_list_item = create_instance_list_entry(instance_name, "firefox");
    instance_list_insert(instances_list, new_instance_list_item);
  }
  gtk_widget_show_all(GTK_WIDGET(instances_list.scrolled_window));
}

void dbus_init()
{
  dbus_connection = g_bus_get_sync(G_BUS_TYPE_SESSION, NULL, NULL);
  if (dbus_connection == NULL)
  {
    g_abort();
  }

  GError *error = NULL;

  bubblejail_manager_proxy = g_dbus_proxy_new_sync(
      dbus_connection,
      G_DBUS_PROXY_FLAGS_NONE,
      &bubblejail_manager_info,
      "org.bubblejail.Manager",
      "/org/bubblejail/manager",
      "org.bubblejail.Manager.Unstable",
      NULL,
      &error);

  if (error != NULL)
  {
    g_abort();
  }
}

static void
activate(GtkApplication *app,
         gpointer G_GNUC_UNUSED user_data)
{
  dbus_init();

  GtkWindow *main_window = GTK_WINDOW(gtk_application_window_new(app));
  gtk_window_set_default_size(main_window, 640, 500);

  GtkHeaderBar *main_header = create_instace_selection_header();
  gtk_window_set_titlebar(main_window, GTK_WIDGET(main_header));

  BubblejailInstanceList instance_list = create_instance_list();

  gtk_container_add(GTK_CONTAINER(main_window), GTK_WIDGET(instance_list.scrolled_window));

  instances_list = instance_list;

  g_dbus_proxy_call(
      bubblejail_manager_proxy,
      "ListInstancesWithDesktopEntries",
      NULL,
      G_DBUS_CALL_FLAGS_NONE,
      1000,
      NULL,
      &update_instaces_list,
      NULL);

  gtk_widget_show_all(GTK_WIDGET(main_window));
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
