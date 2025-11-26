// Views/Controls/TaskCard.xaml.cs
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;

using EisenhowerMatrixPlanner.Core.Entities;
using EisenhowerMatrixPlanner.Services;
using EisenhowerMatrixPlanner.Views.Windows;

using Microsoft.Extensions.DependencyInjection;
// برای TaskEditDialog


// برای GetRequiredService

namespace EisenhowerMatrixPlanner.Views.Controls;
public partial class TaskCard : UserControl {
	public TaskCard() { InitializeComponent(); }

	private async void TaskCard_MouseDoubleClick(object sender, MouseButtonEventArgs e) {
		if (DataContext is not TaskItem task)
			return;
		TaskEditDialog dialog = new TaskEditDialog(task);
		if (dialog.ShowDialog() == true) {
			// دسترسی صحیح به DI
			TaskService? service = App.ServiceProvider?.GetRequiredService<TaskService>();
			Canvas?      canvas  = FindParent<Canvas>(this);
			if (service != null &&
				canvas  != null) {
				service.UpdateCanvasPosition(task, canvas.ActualWidth, canvas.ActualHeight);
				await service.UpdateTaskAsync(task);
			}
		}
	}

	private static T? FindParent<T>(DependencyObject child)
		where T : DependencyObject {
		DependencyObject? parent = VisualTreeHelper.GetParent(child);
		while (parent != null &&
			   parent is not T) {
			parent = VisualTreeHelper.GetParent(parent);
		}
		return parent as T;
	}
}