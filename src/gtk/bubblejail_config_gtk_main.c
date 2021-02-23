#include <gtk/gtk.h>

static void
activate(GtkApplication *app,
         gpointer G_GNUC_UNUSED user_data)
{
  GtkWindow *main_window = GTK_WINDOW(gtk_application_window_new(app));

  GtkHeaderBar *main_header = GTK_HEADER_BAR(gtk_header_bar_new());

  gtk_header_bar_set_title(main_header, "Bubblejail Config");

  gtk_header_bar_set_show_close_button(main_header, TRUE);

  GtkButton *create_button = GTK_BUTTON(gtk_button_new());
  GtkImage *create_button_image = GTK_IMAGE(gtk_image_new_from_icon_name("list-add-symbolic", GTK_ICON_SIZE_BUTTON));
  gtk_button_set_image(create_button, GTK_WIDGET(create_button_image));

  gtk_header_bar_pack_start(main_header, GTK_WIDGET(create_button));
  gtk_window_set_titlebar(main_window, GTK_WIDGET(main_header));

  GtkBox * instance_selection_box = GTK_BOX(gtk_box_new(GTK_ORIENTATION_VERTICAL, 10));
  GtkLabel * instances_label = GTK_LABEL(gtk_label_new("Instances list:"));
  gtk_box_pack_start(instance_selection_box, GTK_WIDGET(instances_label), FALSE, FALSE, 0);

  gtk_container_add(GTK_CONTAINER(main_window), GTK_WIDGET(instance_selection_box));

  GtkListBox *instances_list = GTK_LIST_BOX(gtk_list_box_new());
  gtk_box_pack_end(instance_selection_box, GTK_WIDGET(instances_list), TRUE, TRUE, 0);
  gtk_list_box_set_selection_mode(instances_list, GTK_SELECTION_NONE);

  GtkBox *test_box = GTK_BOX(gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 10));

  gtk_box_set_homogeneous(test_box, FALSE);

  GtkImage *test_image = GTK_IMAGE(gtk_image_new_from_icon_name("firefox", GTK_ICON_SIZE_LARGE_TOOLBAR));
  GtkLabel *test_label = GTK_LABEL(gtk_label_new("Firefox bubble"));
  GtkButton *test_edit_button = GTK_BUTTON(gtk_button_new());
  GtkImage *edit_image = GTK_IMAGE(gtk_image_new_from_icon_name("applications-system-symbolic", GTK_ICON_SIZE_LARGE_TOOLBAR));
  gtk_button_set_image(test_edit_button, GTK_WIDGET(edit_image));

  gtk_box_pack_start(test_box, GTK_WIDGET(test_image), FALSE, TRUE, 0);
  gtk_box_pack_start(test_box, GTK_WIDGET(test_label), FALSE, TRUE, 0);
  gtk_box_pack_end(test_box, GTK_WIDGET(test_edit_button), FALSE, TRUE, 0);

  gtk_list_box_insert(instances_list, GTK_WIDGET(test_box), -1);

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
