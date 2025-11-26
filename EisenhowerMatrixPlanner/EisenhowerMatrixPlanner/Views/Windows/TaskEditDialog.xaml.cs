// Views/Windows/TaskEditDialog.xaml.cs
using System.Windows;

using EisenhowerMatrixPlanner.Core.Entities;


namespace EisenhowerMatrixPlanner.Views.Windows;
public partial class TaskEditDialog : Window {
	public TaskEditDialog(TaskItem task) {
		InitializeComponent();
		DataContext = Task = task;
	}

	public TaskItem Task { get; }

	private void Save_Click(object sender, RoutedEventArgs e) {
		DialogResult = true;
		Close();
	}

	private void Cancel_Click(object sender, RoutedEventArgs e) {
		DialogResult = false;
		Close();
	}
}