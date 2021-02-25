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

static void
activate(GtkApplication *app,
         gpointer G_GNUC_UNUSED user_data)
{
  GtkWindow *main_window = GTK_WINDOW(gtk_application_window_new(app));
  gtk_window_set_default_size(main_window, 640, 500);

  GtkHeaderBar *main_header = create_instace_selection_header();
  gtk_window_set_titlebar(main_window, GTK_WIDGET(main_header));

  BubblejailInstanceList instance_list = create_instance_list();

  gtk_container_add(GTK_CONTAINER(main_window), GTK_WIDGET(instance_list.scrolled_window));

  BubblejailInstanceListItem firefox_test = create_instance_list_entry("Firefox Bubble", "firefox");
  BubblejailInstanceListItem steam_test = create_instance_list_entry("Steam Bubble", "steam");

  instance_list_insert(instance_list, firefox_test);
  instance_list_insert(instance_list, steam_test);

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
